# -*- coding: utf-8 -*-
"""
Tests for Citizen and Officer MCP Tools and Business Logic.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import app as portal
import oauth
from mcp_servers.auth import current_user_var
from mcp_servers.citizen_server import (
    check_eligibility,
    submit_pension_application,
    get_my_application,
    withdraw_my_application,
    check_sla_timeline,
)
from mcp_servers.officer_server import (
    list_applications,
    get_application_details,
    approve_application,
    reject_application,
    get_block_statistics,
)


class TestMCPServers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.citizen_mobile = "9854098765"
        cls.officer_user = "test_bdo"

    def setUp(self):
        # Set citizen context
        self.citizen_ctx_token = current_user_var.set({
            "subject": f"citizen:{self.citizen_mobile}",
            "role": "citizen",
            "scope": "citizen",
            "mobile": self.citizen_mobile,
            "username": None,
        })

    def tearDown(self):
        current_user_var.reset(self.citizen_ctx_token)

    def test_citizen_check_eligibility(self):
        """Test eligibility logic."""
        # Age 65 in Sonari
        res = check_eligibility(age=65, block="Sonari")
        self.assertTrue(res["eligible"])
        self.assertEqual(res["monthly_pension"], "Rs. 250 per month")

        # Underage 55
        res_underage = check_eligibility(age=55, block="Sonari")
        self.assertFalse(res_underage["eligible"])
        self.assertIn("minimum age", res_underage["errors"][0])

        # Invalid block
        res_block = check_eligibility(age=65, block="Nowgong")
        self.assertFalse(res_block["eligible"])
        self.assertIn("outside the scheme pilot area", res_block["errors"][0])

    def test_citizen_submit_and_withdraw_lifecycle(self):
        """Test submission, status tracking, duplicate prevention, and withdrawal."""
        # Clean mobile
        conn = portal.get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM audit_log WHERE application_id IN (SELECT id FROM applications WHERE mobile = %s)", (self.citizen_mobile,))
        cur.execute("DELETE FROM applications WHERE mobile = %s", (self.citizen_mobile,))
        cur.execute("DELETE FROM portal_users WHERE mobile = %s", (self.citizen_mobile,))
        conn.commit(); cur.close(); conn.close()

        # Submit valid application
        sub_res = submit_pension_application(
            applicant_name="Test Applicant Devi",
            dob="10/10/1955",
            gender="Female",
            marital_status="Widowed",
            village="Borbam",
            block="Namti",
            bank_account="123456789012",
            ifsc="SBIN0001234",
        )
        self.assertTrue(sub_res["success"])
        app_id = sub_res["application_id"]
        app_no = sub_res["application_no"]

        # Duplicate submission must be blocked
        dup_res = submit_pension_application(
            applicant_name="Test Applicant Devi",
            dob="10/10/1955",
            gender="Female",
            marital_status="Widowed",
            village="Borbam",
            block="Namti",
            bank_account="123456789012",
            ifsc="SBIN0001234",
        )
        self.assertFalse(dup_res["success"])
        self.assertEqual(dup_res["error_type"], "DUPLICATE_APPLICATION")

        # Track status
        stat_res = get_my_application()
        self.assertTrue(stat_res["found"])
        self.assertEqual(stat_res["status"], "PENDING")
        self.assertEqual(stat_res["application_no"], app_no)

        # Withdraw
        with_res = withdraw_my_application()
        self.assertTrue(with_res["success"])
        self.assertEqual(with_res["status"], "WITHDRAWN")

        # Now citizen can apply again
        re_res = submit_pension_application(
            applicant_name="Test Applicant Devi",
            dob="10/10/1955",
            gender="Female",
            marital_status="Widowed",
            village="Borbam",
            block="Namti",
            bank_account="999988887777",
            ifsc="SBIN0001234",
        )
        self.assertTrue(re_res["success"])

    def test_officer_approval_workflow(self):
        """Test officer review and approval workflow."""
        # Seed an application
        conn = portal.get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM audit_log WHERE application_id IN (SELECT id FROM applications WHERE mobile = '9854000999')")
        cur.execute("DELETE FROM applications WHERE mobile = '9854000999'")
        app_no = "SSP26" + str(portal.random.randint(100000, 999999))
        cur.execute(
            """INSERT INTO applications
               (application_no, applicant_name, mobile, dob, gender, marital_status,
                village, block, bank_account, ifsc, doc_path, status, submitted_at)
               VALUES (%s, 'Officer Test Elder', '9854000999', '1950-01-01', 'Male', 'Married',
                       'Sonari Gaon', 'Sonari', '111122223333', 'SBIN0001234', '/tmp/doc.pdf', 'PENDING', %s)
               RETURNING id""",
            (app_no, portal.now_ist()),
        )
        app_id = cur.fetchone()[0]
        conn.commit(); cur.close(); conn.close()

        # Switch context to officer
        current_user_var.reset(self.citizen_ctx_token)
        officer_token = current_user_var.set({
            "subject": f"officer:{self.officer_user}",
            "role": "officer",
            "scope": "officer",
            "username": self.officer_user,
            "mobile": None,
        })
        try:
            # Details
            details = get_application_details(application_id=app_id)
            self.assertTrue(details["found"])
            self.assertEqual(details["status"], "PENDING")

            # Approve
            justification = "Verified age (76 yrs) and active bank details. Approved."
            appr_res = approve_application(application_id=app_id, justification=justification)
            self.assertTrue(appr_res["success"])
            self.assertEqual(appr_res["status"], "APPROVED")
            self.assertEqual(appr_res["decided_by"], f"officer:{self.officer_user}")

            # Verify in DB
            conn = portal.get_db(); cur = conn.cursor()
            cur.execute("SELECT status, decided_by FROM applications WHERE id = %s", (app_id,))
            row = cur.fetchone()
            cur.execute("SELECT action, actor, note FROM audit_log WHERE application_id = %s AND action = 'APPROVED'", (app_id,))
            audit = cur.fetchone()
            cur.close(); conn.close()

            self.assertEqual(row[0], "APPROVED")
            self.assertEqual(row[1], f"officer:{self.officer_user}")
            self.assertEqual(audit[2], justification)
        finally:
            current_user_var.reset(officer_token)
            # Restore citizen context for tearDown
            self.citizen_ctx_token = current_user_var.set({
                "subject": f"citizen:{self.citizen_mobile}",
                "role": "citizen",
                "scope": "citizen",
                "mobile": self.citizen_mobile,
            })


if __name__ == "__main__":
    unittest.main()
