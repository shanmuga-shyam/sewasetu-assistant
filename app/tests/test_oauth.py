# -*- coding: utf-8 -*-
"""
Tests for Sewa Setu OAuth 2.1 Server implementation.
Verifies RFC 8414 discovery, RFC 7591 client registration, PKCE S256,
RS256 JWT tokens, JWKS verification, and session lifetimes.
"""

import os
import sys
import json
import base64
import hashlib
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import jwt
import app as portal
import oauth


class TestOAuthServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = portal.app.test_client()

    def test_discovery_metadata(self):
        """Test RFC 8414 Authorization Server Metadata."""
        resp = self.client.get("/.well-known/oauth-authorization-server")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("issuer", data)
        self.assertIn("authorization_endpoint", data)
        self.assertIn("token_endpoint", data)
        self.assertIn("jwks_uri", data)
        self.assertIn("citizen", data["scopes_supported"])
        self.assertIn("officer", data["scopes_supported"])
        self.assertIn("S256", data["code_challenge_methods_supported"])

    def test_jwks_keys(self):
        """Test JWKS endpoint returns valid RS256 public key."""
        resp = self.client.get("/.well-known/jwks.json")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("keys", data)
        self.assertGreater(len(data["keys"]), 0)
        key = data["keys"][0]
        self.assertEqual(key["kty"], "RSA")
        self.assertEqual(key["alg"], "RS256")
        self.assertEqual(key["use"], "sig")
        self.assertIn("n", key)
        self.assertIn("e", key)

    def test_client_registration(self):
        """Test Dynamic Client Registration (RFC 7591)."""
        body = {
            "client_name": "Test AI Agent Client",
            "redirect_uris": ["http://localhost:9090/callback"],
            "token_endpoint_auth_method": "none",
        }
        resp = self.client.post("/oauth/register", json=body)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertTrue(data["client_id"].startswith("ssc_"))
        self.assertEqual(data["client_name"], "Test AI Agent Client")

    def test_mint_and_verify_token(self):
        """Test RS256 token minting and signature verification."""
        token, claims = oauth.mint_access_token(
            subject="citizen:9854099999",
            role="citizen",
            scope="citizen",
            audience=oauth.ISSUER,
            client_id="test-client",
        )
        self.assertIsInstance(token, str)
        self.assertEqual(claims["sub"], "citizen:9854099999")
        self.assertEqual(claims["role"], "citizen")

        # Verify using public key
        verified = oauth.verify_token(token, audience=oauth.ISSUER)
        self.assertIsNotNone(verified)
        self.assertEqual(verified["sub"], "citizen:9854099999")
        self.assertEqual(verified["role"], "citizen")

    def test_expired_token_rejected(self):
        """Test expired token is rejected."""
        token, claims = oauth.mint_access_token(
            subject="citizen:9854099999",
            role="citizen",
            scope="citizen",
            audience=oauth.ISSUER,
            client_id="test-client",
            ttl=-10,  # Expired in past
        )
        verified = oauth.verify_token(token, audience=oauth.ISSUER)
        self.assertIsNone(verified)

    def test_audience_mismatch_rejected(self):
        """Test RFC 8707 Resource Indicator / Audience mismatch."""
        token, _ = oauth.mint_access_token(
            subject="citizen:9854099999",
            role="citizen",
            scope="citizen",
            audience="http://service-a.gov.in",
            client_id="test-client",
        )
        # Verifying against different audience must fail
        verified = oauth.verify_token(token, audience="http://service-b.gov.in")
        self.assertIsNone(verified)


if __name__ == "__main__":
    unittest.main()
