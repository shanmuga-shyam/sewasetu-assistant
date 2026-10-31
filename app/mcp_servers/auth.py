# -*- coding: utf-8 -*-
"""
OAuth 2.1 Token Verification and Context Management for MCP Servers.
"""

import os
import sys
import contextvars
from datetime import datetime
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Add parent directory for portal modules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import oauth
import app as portal

current_user_var = contextvars.ContextVar("current_user", default=None)


def get_current_user():
    """Retrieve the authenticated user context for the current request."""
    user = current_user_var.get()
    if not user:
        raise PermissionError("Unauthenticated request: no user context available")
    return user


def verify_mcp_token(token_str: str, expected_role: str, expected_scope: str):
    """
    Verify RS256 token against portal signing keys.
    Validates signature, issuer, expiration, role, and scope.
    """
    if not token_str:
        return None, "Missing authorization token"

    kid, priv = oauth.signing_key()
    pub_key = priv.public_key()

    try:
        # Decode without audience first to inspect claims
        unverified_claims = jwt.decode(
            token_str, options={"verify_signature": False, "verify_aud": False}
        )
    except jwt.PyJWTError as e:
        return None, f"Malformed token: {e}"

    # Verify signature and expiration
    try:
        claims = jwt.decode(
            token_str,
            pub_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # We validate aud flexibly below
        )
    except jwt.ExpiredSignatureError:
        return None, "Token has expired"
    except jwt.PyJWTError as e:
        return None, f"Invalid token signature: {e}"

    # Validate Issuer
    issuer = claims.get("iss", "")
    expected_issuer = oauth.ISSUER
    if issuer.rstrip("/") != expected_issuer.rstrip("/"):
        # Also allow localhost variant
        if not ("localhost" in issuer and "localhost" in expected_issuer):
            return None, f"Issuer mismatch: got {issuer}, expected {expected_issuer}"

    # Validate Role and Scope
    role = claims.get("role")
    scope = claims.get("scope")
    if role != expected_role:
        return None, f"Role mismatch: required {expected_role}, got {role}"
    if scope != expected_scope and expected_scope not in (scope or "").split():
        return None, f"Scope mismatch: required {expected_scope}, got {scope}"

    subject = claims.get("sub", "")
    if ":" in subject:
        sub_role, sub_identifier = subject.split(":", 1)
    else:
        sub_role = role
        sub_identifier = subject

    user_info = {
        "subject": subject,
        "role": role,
        "scope": scope,
        "identifier": sub_identifier,
        "client_id": claims.get("client_id", ""),
        "jti": claims.get("jti", ""),
        "claims": claims,
    }

    if role == "citizen":
        user_info["mobile"] = sub_identifier
    elif role == "officer":
        user_info["username"] = sub_identifier

    return user_info, None


class MCPAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, expected_role: str, expected_scope: str, server_name: str):
        super().__init__(app)
        self.expected_role = expected_role
        self.expected_scope = expected_scope
        self.server_name = server_name

    async def dispatch(self, request: Request, call_next):
        # Allow CORS preflight OPTIONS requests unconditionally
        if request.method == "OPTIONS":
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            return response

        # Extract token from Authorization header or URL query parameter
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif "token" in request.query_params:
            token = request.query_params.get("token", "").strip()

        user_info, error = verify_mcp_token(token, self.expected_role, self.expected_scope)
        if error:
            resp = JSONResponse(
                {
                    "error": "unauthorized",
                    "error_description": error,
                    "server": self.server_name,
                    "expected_role": self.expected_role,
                    "expected_scope": self.expected_scope,
                },
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer realm="SewaSetu", error="invalid_token", error_description="{error}"',
                    "Access-Control-Allow-Origin": "*",
                },
            )
            return resp

        # Set user context for the duration of this request
        token_ctx = current_user_var.set(user_info)
        try:
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
        finally:
            current_user_var.reset(token_ctx)
