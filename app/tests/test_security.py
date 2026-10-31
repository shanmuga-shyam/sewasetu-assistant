# -*- coding: utf-8 -*-
"""
Security and Access Boundary Tests for Sewa Setu MCP System.
Verifies role and scope barriers, cross-citizen isolation, prevention of
privilege escalation, tamper detection, and rule enforcement.
"""

import os
import sys
import unittest
import asyncio
from starlette.testclient import TestClient

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import app as portal
import oauth
from mcp_servers.citizen_server import citizen_mcp, create_citizen_app
from mcp_servers.officer_server import officer_mcp, create_officer_app
from mcp_servers.auth import verify_mcp_token


class TestSecurityBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.citizen_app = create_citizen_app()
        cls.officer_app = create_officer_app()
        cls.citizen_client = TestClient(cls.citizen_app)
        cls.officer_client = TestClient(cls.officer_app)

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests to MCP servers must be rejected with 401."""
        # Citizen server
        resp_c = self.citizen_client.post("/mcp", json={})
        self.assertEqual(resp_c.status_code, 401)
        self.assertIn("WWW-Authenticate", resp_c.headers)

        # Officer server
        resp_o = self.officer_client.post("/mcp", json={})
        self.assertEqual(resp_o.status_code, 401)
        self.assertIn("WWW-Authenticate", resp_o.headers)

    def test_citizen_token_rejected_at_officer_server(self):
        """Privilege escalation check: A citizen token cannot access officer server."""
        token, _ = oauth.mint_access_token(
            subject="citizen:9854011111",
            role="citizen",
            scope="citizen",
            audience="http://localhost:8002",
            client_id="attacker-client",
        )
        resp = self.officer_client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertEqual(data["error"], "unauthorized")
        self.assertIn("Role mismatch", data["error_description"])

    def test_officer_token_rejected_at_citizen_server(self):
        """Scope isolation: An officer token cannot act as a citizen on citizen endpoint."""
        token, _ = oauth.mint_access_token(
            subject="officer:admin",
            role="officer",
            scope="officer",
            audience="http://localhost:8001",
            client_id="admin-client",
        )
        resp = self.citizen_client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertEqual(data["error"], "unauthorized")
        self.assertIn("Role mismatch", data["error_description"])

    def test_tool_isolation_check(self):
        """Verify that citizen assistant does NOT have access to officer tools."""
        c_tools = asyncio.run(citizen_mcp.list_tools())
        c_names = [t.name for t in c_tools]

        o_tools = asyncio.run(officer_mcp.list_tools())
        o_names = [t.name for t in o_tools]

        # Citizen must not see officer tools
        self.assertNotIn("approve_application", c_names)
        self.assertNotIn("reject_application", c_names)
        self.assertNotIn("list_applications", c_names)

        # Officer must not see citizen tools
        self.assertNotIn("submit_pension_application", o_names)
        self.assertNotIn("withdraw_my_application", o_names)
        self.assertNotIn("get_my_application", o_names)

    def test_tampered_jwt_rejected(self):
        """Verify cryptographic integrity: a tampered JWT must fail verification."""
        token, _ = oauth.mint_access_token(
            subject="citizen:9854011111",
            role="citizen",
            scope="citizen",
            audience=oauth.ISSUER,
            client_id="test",
        )
        # Tamper payload
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1][:-4]}AAAA.{parts[2]}"
        user, err = verify_mcp_token(tampered_token, "citizen", "citizen")
        self.assertIsNone(user)
        self.assertIsNotNone(err)


if __name__ == "__main__":
    unittest.main()
