# -*- coding: utf-8 -*-
"""
Sewa Setu MCP Client Evaluator.
Executes multi-turn evaluation of synthetic citizen and officer personas
through an actual MCP Streamable HTTP client session, verifying PostgreSQL
database states and audit trails before and after every interaction.
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime, timedelta

# Path configuration
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import psycopg2
import httpx2
from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession

import oauth
import app as portal
from evals.personas import PERSONAS, OFFICER_PERSONAS

RESULTS_FILE = os.path.join(CURRENT_DIR, "results.json")


def setup_persona_db_state(persona):
    """Seed or clean database state before evaluating each persona."""
    conn = portal.get_db()
    cur = conn.cursor()
    p_id = persona["id"]
    mobile = persona.get("mobile")

    try:
        if p_id in ("persona_1_phuleswari", "persona_4_ramakant", "persona_6_dimbeswar",
                    "persona_7_arati", "persona_8_joyprakash"):
            # Clean state: remove any prior test applications and portal_users
            cur.execute("DELETE FROM audit_log WHERE application_id IN (SELECT id FROM applications WHERE mobile = %s)", (mobile,))
            cur.execute("DELETE FROM applications WHERE mobile = %s", (mobile,))
            cur.execute("DELETE FROM portal_users WHERE mobile = %s", (mobile,))
            cur.execute("DELETE FROM otps WHERE mobile = %s", (mobile,))

        elif p_id == "persona_2_bhabesh":
            # Seed 1 pending application submitted 4 days ago
            cur.execute("DELETE FROM audit_log WHERE application_id IN (SELECT id FROM applications WHERE mobile = %s)", (mobile,))
            cur.execute("DELETE FROM applications WHERE mobile = %s", (mobile,))
            cur.execute("DELETE FROM portal_users WHERE mobile = %s", (mobile,))

            app_no = "SSP26" + str(portal.random.randint(100000, 999999))
            sub_at = portal.now_ist() - timedelta(days=4)
            cur.execute(
                """INSERT INTO applications
                   (application_no, applicant_name, mobile, dob, gender, marital_status,
                    village, block, bank_account, ifsc, doc_path, status, submitted_at)
                   VALUES (%s, %s, %s, %s, 'Male', 'Married', 'Koliabor', 'Rajapara',
                           '30129845671', 'CBIN0280123', '/tmp/doc.pdf', 'PENDING', %s)
                   RETURNING id""",
                (app_no, persona["name"], mobile, portal.parse_dob(persona["dob"]), sub_at),
            )
            new_id = cur.fetchone()[0]
            portal.write_audit(cur, new_id, "SUBMIT", f"applicant:{mobile}", "Portal web submission")

        elif p_id == "persona_3_tarulata":
            # Seed 1 pending application with the old wrong account submitted 1 day ago
            cur.execute("DELETE FROM audit_log WHERE application_id IN (SELECT id FROM applications WHERE mobile = %s)", (mobile,))
            cur.execute("DELETE FROM applications WHERE mobile = %s", (mobile,))
            cur.execute("DELETE FROM portal_users WHERE mobile = %s", (mobile,))

            app_no = "SSP26" + str(portal.random.randint(100000, 999999))
            sub_at = portal.now_ist() - timedelta(days=1)
            cur.execute(
                """INSERT INTO applications
                   (application_no, applicant_name, mobile, dob, gender, marital_status,
                    husband_name, village, block, bank_account, ifsc, doc_path, status, submitted_at)
                   VALUES (%s, %s, %s, %s, 'Female', 'Widowed', 'Late Naren Gogoi', 'Borbam', 'Namti',
                           %s, 'UBIN0532101', '/tmp/doc.pdf', 'PENDING', %s)
                   RETURNING id""",
                (app_no, persona["name"], mobile, portal.parse_dob(persona["dob"]),
                 persona["bank_account_old"], sub_at),
            )
            new_id = cur.fetchone()[0]
            portal.write_audit(cur, new_id, "SUBMIT", f"applicant:{mobile}", "Initial submission with error")

        elif p_id == "persona_5_minati":
            # Seed 1 application pending 22 days ago (overdue SLA)
            cur.execute("DELETE FROM audit_log WHERE application_id IN (SELECT id FROM applications WHERE mobile = %s)", (mobile,))
            cur.execute("DELETE FROM applications WHERE mobile = %s", (mobile,))
            cur.execute("DELETE FROM portal_users WHERE mobile = %s", (mobile,))

            app_no = "SSP26" + str(portal.random.randint(100000, 999999))
            sub_at = portal.now_ist() - timedelta(days=22)
            cur.execute(
                """INSERT INTO applications
                   (application_no, applicant_name, mobile, dob, gender, marital_status,
                    husband_name, village, block, bank_account, ifsc, doc_path, status, submitted_at)
                   VALUES (%s, %s, %s, %s, 'Female', 'Widowed', 'Late Dhireswar Barua', 'Charaideo', 'Sonari',
                           '20349811234', 'PUNB0123400', '/tmp/doc.pdf', 'PENDING', %s)
                   RETURNING id""",
                (app_no, persona["name"], mobile, portal.parse_dob(persona["dob"]), sub_at),
            )
            new_id = cur.fetchone()[0]
            portal.write_audit(cur, new_id, "SUBMIT", f"applicant:{mobile}", "Submitted via kiosk")

        elif p_id == "persona_9_malati":
            # Seed 1 APPROVED application
            cur.execute("DELETE FROM audit_log WHERE application_id IN (SELECT id FROM applications WHERE mobile = %s)", (mobile,))
            cur.execute("DELETE FROM applications WHERE mobile = %s", (mobile,))
            cur.execute("DELETE FROM portal_users WHERE mobile = %s", (mobile,))

            app_no = "SSP26" + str(portal.random.randint(100000, 999999))
            sub_at = portal.now_ist() - timedelta(days=10)
            dec_at = portal.now_ist() - timedelta(days=3)
            cur.execute(
                """INSERT INTO applications
                   (application_no, applicant_name, mobile, dob, gender, marital_status,
                    husband_name, village, block, bank_account, ifsc, doc_path, status, submitted_at,
                    decided_at, decided_by)
                   VALUES (%s, %s, %s, %s, 'Female', 'Widowed', 'Late Bipul Medhi', 'Sepon', 'Sonari',
                           '777788889999', 'SBIN0007890', '/tmp/doc.pdf', 'APPROVED', %s, %s, 'officer:admin')
                   RETURNING id""",
                (app_no, persona["name"], mobile, portal.parse_dob(persona["dob"]), sub_at, dec_at),
            )
            new_id = cur.fetchone()[0]
            portal.write_audit(cur, new_id, "SUBMIT", f"applicant:{mobile}", "Counter submission")
            portal.write_audit(cur, new_id, "APPROVED", "officer:admin", "Age 76 verified from Voter ID. All documents in order.")

        elif p_id == "persona_10_jagannath":
            # Seed 1 existing active approved application
            cur.execute("DELETE FROM audit_log WHERE application_id IN (SELECT id FROM applications WHERE mobile = %s)", (mobile,))
            cur.execute("DELETE FROM applications WHERE mobile = %s", (mobile,))
            cur.execute("DELETE FROM portal_users WHERE mobile = %s", (mobile,))

            app_no = "SSP25" + str(portal.random.randint(100000, 999999))
            sub_at = portal.now_ist() - timedelta(days=120)
            dec_at = portal.now_ist() - timedelta(days=110)
            cur.execute(
                """INSERT INTO applications
                   (application_no, applicant_name, mobile, dob, gender, marital_status,
                    village, block, bank_account, ifsc, doc_path, status, submitted_at, decided_at, decided_by)
                   VALUES (%s, %s, %s, %s, 'Male', 'Married', 'Salaguri', 'Namti',
                           '888899990000', 'SBIN0009999', '/tmp/doc.pdf', 'APPROVED', %s, %s, 'officer:admin')
                   RETURNING id""",
                (app_no, persona["name"], mobile, portal.parse_dob(persona["dob"]), sub_at, dec_at),
            )
            new_id = cur.fetchone()[0]
            portal.write_audit(cur, new_id, "SUBMIT", f"applicant:{mobile}", "Previous batch application")
            portal.write_audit(cur, new_id, "APPROVED", "officer:admin", "Approved")

        conn.commit()
    finally:
        cur.close()
        conn.close()


async def evaluate_persona(persona, citizen_endpoint_url):
    """Run full evaluation for a citizen persona via real MCP client."""
    p_id = persona["id"]
    mobile = persona["mobile"]
    start_time = time.time()

    # 1. Setup DB state
    setup_persona_db_state(persona)

    # 2. Mint OAuth Token for this citizen
    token, claims = oauth.mint_access_token(
        subject=f"citizen:{mobile}",
        role="citizen",
        scope="citizen",
        audience=citizen_endpoint_url,
        client_id="eval-claude-code-client",
        ttl=3600,
    )

    transcript = []
    checks = []
    passed = True
    failure_reasons = []

    # 3. Connect via MCP client
    try:
        async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=20.0) as http_client:
            async with streamable_http_client(citizen_endpoint_url, http_client=http_client) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    intent = persona["intent"]

                    if intent == "fresh_application":
                        # Turn 1: Check eligibility
                        t1_args = {"age": persona["age"], "dob": persona["dob"], "block": persona["block"]}
                        t1_res = await session.call_tool("check_eligibility", t1_args)
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]
                        transcript.append({
                            "turn": 1,
                            "speaker": "citizen",
                            "message": persona["dialogue_prompt"],
                            "tool_called": "check_eligibility",
                            "tool_args": t1_args,
                            "tool_result": t1_data,
                        })

                        # Turn 2: Submit application
                        t2_args = {
                            "applicant_name": persona["name"],
                            "dob": persona["dob"],
                            "gender": persona["gender"],
                            "marital_status": persona["marital_status"],
                            "husband_name": persona["husband_name"],
                            "village": persona["village"],
                            "block": persona["block"],
                            "bank_account": persona["bank_account"],
                            "ifsc": persona["ifsc"],
                            "age_proof_doc_name": "aadhaar_phuleswari.pdf",
                        }
                        t2_res = await session.call_tool("submit_pension_application", t2_args)
                        t2_data = json.loads(t2_res.content[0].text) if hasattr(t2_res.content[0], "text") else t2_res.content[0]
                        transcript.append({
                            "turn": 2,
                            "speaker": "assistant",
                            "message": f"Eligibility confirmed for {persona['name']}. Submitting application...",
                            "tool_called": "submit_pension_application",
                            "tool_args": t2_args,
                            "tool_result": t2_data,
                        })

                        # Verify DB
                        conn = portal.get_db(); cur = conn.cursor()
                        cur.execute("SELECT application_no, status, applicant_name, block FROM applications WHERE mobile = %s", (mobile,))
                        row = cur.fetchone()
                        cur.execute("SELECT count(*) FROM audit_log WHERE application_id IN (SELECT id FROM applications WHERE mobile = %s) AND action = 'SUBMIT'", (mobile,))
                        audit_count = cur.fetchone()[0]
                        cur.execute("SELECT count(*) FROM portal_users WHERE mobile = %s", (mobile,))
                        user_count = cur.fetchone()[0]
                        cur.close(); conn.close()

                        db_ok = row is not None and row[1] == "PENDING" and row[2] == persona["name"] and audit_count >= 1 and user_count >= 1
                        checks.append({
                            "name": "Database Row Inserted & Audited",
                            "passed": db_ok,
                            "details": f"App: {row[0] if row else 'None'}, Status: {row[1] if row else 'None'}, Audit entries: {audit_count}, Portal user: {user_count}",
                        })
                        if not db_ok:
                            passed = False
                            failure_reasons.append("Application not found in database or audit/user missing")

                    elif intent == "status_check":
                        # Turn 1: Get my application
                        t1_res = await session.call_tool("get_my_application", {})
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]
                        transcript.append({
                            "turn": 1,
                            "speaker": "citizen",
                            "message": persona["dialogue_prompt"],
                            "tool_called": "get_my_application",
                            "tool_args": {},
                            "tool_result": t1_data,
                        })

                        conn = portal.get_db(); cur = conn.cursor()
                        cur.execute("SELECT count(*) FROM applications WHERE mobile = %s", (mobile,))
                        app_count = cur.fetchone()[0]
                        cur.close(); conn.close()

                        db_ok = (app_count == 1) and (t1_data.get("status") == "PENDING")
                        checks.append({
                            "name": "Single Pending Record Retrieved Intact",
                            "passed": db_ok,
                            "details": f"Status retrieved: {t1_data.get('status')}, DB count: {app_count}",
                        })
                        if not db_ok:
                            passed = False
                            failure_reasons.append("Failed to retrieve existing pending application")

                    elif intent == "withdraw_and_reapply":
                        # Turn 1: Check existing
                        t1_res = await session.call_tool("get_my_application", {})
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]

                        # Turn 2: Withdraw
                        t2_res = await session.call_tool("withdraw_my_application", {})
                        t2_data = json.loads(t2_res.content[0].text) if hasattr(t2_res.content[0], "text") else t2_res.content[0]
                        transcript.append({
                            "turn": 1,
                            "speaker": "citizen",
                            "message": persona["dialogue_prompt"],
                            "tool_called": "withdraw_my_application",
                            "tool_args": {},
                            "tool_result": t2_data,
                        })

                        # Turn 3: Reapply with corrected bank details
                        t3_args = {
                            "applicant_name": persona["name"],
                            "dob": persona["dob"],
                            "gender": persona["gender"],
                            "marital_status": persona["marital_status"],
                            "husband_name": persona["husband_name"],
                            "village": persona["village"],
                            "block": persona["block"],
                            "bank_account": persona["bank_account_new"],
                            "ifsc": persona["ifsc"],
                            "age_proof_doc_name": "passbook_corrected.pdf",
                        }
                        t3_res = await session.call_tool("submit_pension_application", t3_args)
                        t3_data = json.loads(t3_res.content[0].text) if hasattr(t3_res.content[0], "text") else t3_res.content[0]
                        transcript.append({
                            "turn": 2,
                            "speaker": "assistant",
                            "message": "Previous application withdrawn. Now submitting fresh application with updated bank details.",
                            "tool_called": "submit_pension_application",
                            "tool_args": t3_args,
                            "tool_result": t3_data,
                        })

                        conn = portal.get_db(); cur = conn.cursor()
                        cur.execute("SELECT status, decided_by, bank_account FROM applications WHERE mobile = %s ORDER BY id ASC", (mobile,))
                        rows = cur.fetchall()
                        cur.close(); conn.close()

                        db_ok = (len(rows) == 2 and rows[0][0] == "WITHDRAWN" and rows[0][1] == "APPLICANT"
                                 and rows[1][0] == "PENDING" and rows[1][2] == persona["bank_account_new"])
                        checks.append({
                            "name": "Withdrawal & Clean Resubmission in Database",
                            "passed": db_ok,
                            "details": f"Total rows: {len(rows)}, App 1: {rows[0] if rows else None}, App 2: {rows[1] if len(rows) > 1 else None}",
                        })
                        if not db_ok:
                            passed = False
                            failure_reasons.append("Withdrawal and reapplication lifecycle failed in database")

                    elif intent == "underage_attempt":
                        # Turn 1: Check eligibility
                        t1_args = {"age": persona["age"], "dob": persona["dob"], "block": persona["block"]}
                        t1_res = await session.call_tool("check_eligibility", t1_args)
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]
                        transcript.append({
                            "turn": 1,
                            "speaker": "citizen",
                            "message": persona["dialogue_prompt"],
                            "tool_called": "check_eligibility",
                            "tool_args": t1_args,
                            "tool_result": t1_data,
                        })

                        # Attempt submission anyway to test validation boundary
                        t2_args = {
                            "applicant_name": persona["name"],
                            "dob": persona["dob"],
                            "gender": persona["gender"],
                            "marital_status": persona["marital_status"],
                            "village": persona["village"],
                            "block": persona["block"],
                            "bank_account": persona["bank_account"],
                            "ifsc": persona["ifsc"],
                        }
                        t2_res = await session.call_tool("submit_pension_application", t2_args)
                        t2_data = json.loads(t2_res.content[0].text) if hasattr(t2_res.content[0], "text") else t2_res.content[0]
                        transcript.append({
                            "turn": 2,
                            "speaker": "assistant",
                            "message": "Testing submission for underage applicant; expecting rejection.",
                            "tool_called": "submit_pension_application",
                            "tool_args": t2_args,
                            "tool_result": t2_data,
                        })

                        conn = portal.get_db(); cur = conn.cursor()
                        cur.execute("SELECT count(*) FROM applications WHERE mobile = %s", (mobile,))
                        count = cur.fetchone()[0]
                        cur.close(); conn.close()

                        db_ok = (count == 0) and (t2_data.get("success") is False)
                        checks.append({
                            "name": "Underage Rejection (Rule Enforcement)",
                            "passed": db_ok,
                            "details": f"Tool success: {t2_data.get('success')}, DB row count: {count}",
                        })
                        if not db_ok:
                            passed = False
                            failure_reasons.append("Underage applicant was incorrectly accepted")

                    elif intent == "sla_inquiry":
                        # Turn 1: Check SLA timeline
                        t1_res = await session.call_tool("check_sla_timeline", {})
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]
                        transcript.append({
                            "turn": 1,
                            "speaker": "citizen",
                            "message": persona["dialogue_prompt"],
                            "tool_called": "check_sla_timeline",
                            "tool_args": {},
                            "tool_result": t1_data,
                        })

                        sla_ok = t1_data.get("is_overdue") is True and t1_data.get("deemed_approval_eligible") is True
                        checks.append({
                            "name": "Statutory SLA Overdue & Deemed Approval Identified",
                            "passed": sla_ok,
                            "details": f"Overdue: {t1_data.get('is_overdue')}, Days elapsed: {t1_data.get('days_elapsed')}",
                        })
                        if not sla_ok:
                            passed = False
                            failure_reasons.append("SLA calculation failed to flag 22-day overdue application")

                    elif intent == "kiosk_submission":
                        # Turn 1: Submit application with acknowledgment request
                        t1_args = {
                            "applicant_name": persona["name"],
                            "dob": persona["dob"],
                            "gender": persona["gender"],
                            "marital_status": persona["marital_status"],
                            "village": persona["village"],
                            "block": persona["block"],
                            "bank_account": persona["bank_account"],
                            "ifsc": persona["ifsc"],
                            "age_proof_doc_name": "aadhaar_dimbeswar.pdf",
                        }
                        t1_res = await session.call_tool("submit_pension_application", t1_args)
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]

                        # Turn 2: Get acknowledgment
                        t2_res = await session.call_tool("get_application_acknowledgment", {})
                        t2_data = json.loads(t2_res.content[0].text) if hasattr(t2_res.content[0], "text") else t2_res.content[0]
                        transcript.append({
                            "turn": 1,
                            "speaker": "kiosk_operator",
                            "message": persona["dialogue_prompt"],
                            "tool_called": "submit_pension_application",
                            "tool_args": t1_args,
                            "tool_result": t1_data,
                        })
                        transcript.append({
                            "turn": 2,
                            "speaker": "assistant",
                            "message": "Application created; retrieving computer-generated acknowledgment slip.",
                            "tool_called": "get_application_acknowledgment",
                            "tool_args": {},
                            "tool_result": t2_data,
                        })

                        conn = portal.get_db(); cur = conn.cursor()
                        cur.execute("SELECT status, block FROM applications WHERE mobile = %s", (mobile,))
                        row = cur.fetchone()
                        cur.close(); conn.close()

                        db_ok = row is not None and row[0] == "PENDING" and row[1] == "Dhemaji Pathar" and t2_data.get("found") is True
                        checks.append({
                            "name": "Kiosk Submission & Acknowledgment Slip",
                            "passed": db_ok,
                            "details": f"Status: {row[0] if row else None}, Ack URL: {t2_data.get('download_pdf_url')}",
                        })
                        if not db_ok:
                            passed = False
                            failure_reasons.append("Kiosk submission or acknowledgment slip generation failed")

                    elif intent == "invalid_block_attempt":
                        # Turn 1: Try submission with invalid block
                        t1_args = {
                            "applicant_name": persona["name"],
                            "dob": persona["dob"],
                            "gender": persona["gender"],
                            "marital_status": persona["marital_status"],
                            "husband_name": persona["husband_name"],
                            "village": persona["village"],
                            "block": persona["block"],
                            "bank_account": persona["bank_account"],
                            "ifsc": persona["ifsc"],
                        }
                        t1_res = await session.call_tool("submit_pension_application", t1_args)
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]
                        transcript.append({
                            "turn": 1,
                            "speaker": "citizen",
                            "message": persona["dialogue_prompt"],
                            "tool_called": "submit_pension_application",
                            "tool_args": t1_args,
                            "tool_result": t1_data,
                        })

                        conn = portal.get_db(); cur = conn.cursor()
                        cur.execute("SELECT count(*) FROM applications WHERE mobile = %s", (mobile,))
                        count = cur.fetchone()[0]
                        cur.close(); conn.close()

                        db_ok = (count == 0) and (t1_data.get("success") is False)
                        checks.append({
                            "name": "Invalid Pilot Block Rejected",
                            "passed": db_ok,
                            "details": f"Tool error: {t1_data.get('errors')}, DB count: {count}",
                        })
                        if not db_ok:
                            passed = False
                            failure_reasons.append("Application outside pilot blocks was erroneously accepted")

                    elif intent == "ifsc_correction_submission":
                        # Turn 1: Submit with corrected valid IFSC
                        t1_args = {
                            "applicant_name": persona["name"],
                            "dob": persona["dob"],
                            "gender": persona["gender"],
                            "marital_status": persona["marital_status"],
                            "village": persona["village"],
                            "block": persona["block"],
                            "bank_account": persona["bank_account"],
                            "ifsc": persona["ifsc_valid"],
                        }
                        t1_res = await session.call_tool("submit_pension_application", t1_args)
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]
                        transcript.append({
                            "turn": 1,
                            "speaker": "citizen",
                            "message": persona["dialogue_prompt"],
                            "tool_called": "submit_pension_application",
                            "tool_args": t1_args,
                            "tool_result": t1_data,
                        })

                        conn = portal.get_db(); cur = conn.cursor()
                        cur.execute("SELECT ifsc, status FROM applications WHERE mobile = %s", (mobile,))
                        row = cur.fetchone()
                        cur.close(); conn.close()

                        db_ok = row is not None and row[0] == "PUNB0012345" and row[1] == "PENDING"
                        checks.append({
                            "name": "Standardized Uppercase 11-Digit IFSC Stored",
                            "passed": db_ok,
                            "details": f"Stored IFSC: {row[0] if row else None}, Status: {row[1] if row else None}",
                        })
                        if not db_ok:
                            passed = False
                            failure_reasons.append("Normalized IFSC submission failed")

                    elif intent == "approved_inquiry":
                        # Turn 1: Get my application
                        t1_res = await session.call_tool("get_my_application", {})
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]
                        transcript.append({
                            "turn": 1,
                            "speaker": "citizen",
                            "message": persona["dialogue_prompt"],
                            "tool_called": "get_my_application",
                            "tool_args": {},
                            "tool_result": t1_data,
                        })

                        db_ok = t1_data.get("status") == "APPROVED" and t1_data.get("decided_by") == "officer:admin"
                        checks.append({
                            "name": "Approved Status & Officer Decision Recorded",
                            "passed": db_ok,
                            "details": f"Status: {t1_data.get('status')}, Decided by: {t1_data.get('decided_by')}",
                        })
                        if not db_ok:
                            passed = False
                            failure_reasons.append("Approved inquiry could not find decision record")

                    elif intent == "duplicate_prevention":
                        # Turn 1: Attempt duplicate submission
                        t1_args = {
                            "applicant_name": persona["name"],
                            "dob": persona["dob"],
                            "gender": persona["gender"],
                            "marital_status": persona["marital_status"],
                            "village": persona["village"],
                            "block": persona["block"],
                            "bank_account": persona["bank_account"],
                            "ifsc": persona["ifsc"],
                        }
                        t1_res = await session.call_tool("submit_pension_application", t1_args)
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]
                        transcript.append({
                            "turn": 1,
                            "speaker": "citizen",
                            "message": persona["dialogue_prompt"],
                            "tool_called": "submit_pension_application",
                            "tool_args": t1_args,
                            "tool_result": t1_data,
                        })

                        conn = portal.get_db(); cur = conn.cursor()
                        cur.execute("SELECT count(*) FROM applications WHERE mobile = %s", (mobile,))
                        count = cur.fetchone()[0]
                        cur.close(); conn.close()

                        db_ok = (count == 1) and (t1_data.get("error_type") == "DUPLICATE_APPLICATION")
                        checks.append({
                            "name": "Duplicate Active Application Blocked",
                            "passed": db_ok,
                            "details": f"Error type: {t1_data.get('error_type')}, Total DB rows: {count}",
                        })
                        if not db_ok:
                            passed = False
                            failure_reasons.append("Duplicate application was not prevented")

    except Exception as e:
        passed = False
        failure_reasons.append(f"Evaluation execution exception: {str(e)}")
        checks.append({"name": "Execution Exception", "passed": False, "details": str(e)})

    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "persona_id": p_id,
        "name": persona["name"],
        "age": persona["age"],
        "village": persona["village"],
        "block": persona["block"],
        "mobile": mobile,
        "language_style": persona["language_style"],
        "intent": persona["intent"],
        "passed": passed,
        "duration_ms": duration_ms,
        "failure_reasons": failure_reasons,
        "checks": checks,
        "transcript": transcript,
    }


async def evaluate_officer(officer, officer_endpoint_url):
    """Run evaluation for an officer persona via real MCP client."""
    start_time = time.time()
    username = officer["username"]

    # Mint officer token
    token, claims = oauth.mint_access_token(
        subject=f"officer:{username}",
        role="officer",
        scope="officer",
        audience=officer_endpoint_url,
        client_id="eval-claude-officer-client",
        ttl=3600,
    )

    transcript = []
    checks = []
    passed = True
    failure_reasons = []

    try:
        async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=20.0) as http_client:
            async with streamable_http_client(officer_endpoint_url, http_client=http_client) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    if officer["intent"] == "officer_approval":
                        # Turn 1: Find Phuleswari's application (submitted earlier in eval)
                        t1_res = await session.call_tool("search_applications", {"query": "9854011221"})
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]
                        app_id = t1_data["results"][0]["application_id"] if t1_data.get("results") else None

                        # Turn 2: Inspect document
                        t2_data = {}
                        if app_id:
                            t2_res = await session.call_tool("review_application_document", {"application_id": app_id})
                            t2_data = json.loads(t2_res.content[0].text) if hasattr(t2_res.content[0], "text") else t2_res.content[0]

                        # Turn 3: Approve application
                        t3_data = {}
                        justification = "Aadhaar verified age 71, valid SBI account in Sonari block. Approved under Purvanchal RTPS Act."
                        if app_id:
                            t3_res = await session.call_tool("approve_application", {"application_id": app_id, "justification": justification})
                            t3_data = json.loads(t3_res.content[0].text) if hasattr(t3_res.content[0], "text") else t3_res.content[0]

                        transcript.append({
                            "turn": 1,
                            "speaker": "officer",
                            "message": officer["dialogue_prompt"],
                            "tool_called": "search_applications",
                            "tool_result": t1_data,
                        })
                        transcript.append({
                            "turn": 2,
                            "speaker": "assistant",
                            "message": f"Found application ID {app_id}; inspecting age proof and approving.",
                            "tool_called": "approve_application",
                            "tool_result": t3_data,
                        })

                        conn = portal.get_db(); cur = conn.cursor()
                        cur.execute("SELECT status, decided_by FROM applications WHERE id = %s", (app_id,))
                        row = cur.fetchone()
                        cur.execute("SELECT action, actor, note FROM audit_log WHERE application_id = %s AND action = 'APPROVED'", (app_id,))
                        audit_row = cur.fetchone()
                        cur.close(); conn.close()

                        db_ok = row is not None and row[0] == "APPROVED" and row[1] == f"officer:{username}" and audit_row is not None
                        checks.append({
                            "name": "Officer Approval & Audit Trail Stamp in DB",
                            "passed": db_ok,
                            "details": f"Status: {row[0] if row else None}, Decided by: {row[1] if row else None}, Audit note: {audit_row[2] if audit_row else None}",
                        })
                        if not db_ok:
                            passed = False
                            failure_reasons.append("Officer approval failed in database")

                    elif officer["intent"] == "officer_queue_monitoring":
                        # Turn 1: Get block statistics
                        t1_res = await session.call_tool("get_block_statistics", {})
                        t1_data = json.loads(t1_res.content[0].text) if hasattr(t1_res.content[0], "text") else t1_res.content[0]

                        # Turn 2: List overdue applications
                        t2_res = await session.call_tool("list_applications", {"block": "Rajapara", "overdue_only": True, "limit": 10})
                        t2_data = json.loads(t2_res.content[0].text) if hasattr(t2_res.content[0], "text") else t2_res.content[0]

                        transcript.append({
                            "turn": 1,
                            "speaker": "officer",
                            "message": officer["dialogue_prompt"],
                            "tool_called": "get_block_statistics",
                            "tool_result": t1_data,
                        })
                        transcript.append({
                            "turn": 2,
                            "speaker": "assistant",
                            "message": "Retrieved statistics and overdue queue for Rajapara.",
                            "tool_called": "list_applications",
                            "tool_result": t2_data,
                        })

                        stats_ok = t1_data.get("total_applications", 0) > 0 and "status_distribution" in t1_data
                        checks.append({
                            "name": "Queue Metrics & Block Statistics Query",
                            "passed": stats_ok,
                            "details": f"Total: {t1_data.get('total_applications')}, Overdue pending: {t1_data.get('sla_overdue_pending')}",
                        })
                        if not stats_ok:
                            passed = False
                            failure_reasons.append("Officer failed to query queue metrics")

    except Exception as e:
        passed = False
        failure_reasons.append(f"Officer eval execution exception: {str(e)}")
        checks.append({"name": "Officer Execution Exception", "passed": False, "details": str(e)})

    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "persona_id": officer["id"],
        "name": officer["name"],
        "username": username,
        "jurisdiction": officer.get("jurisdiction", "All"),
        "intent": officer["intent"],
        "passed": passed,
        "duration_ms": duration_ms,
        "failure_reasons": failure_reasons,
        "checks": checks,
        "transcript": transcript,
    }


async def run_all_evaluations(citizen_url="http://127.0.0.1:8001/mcp", officer_url="http://127.0.0.1:8002/mcp"):
    """Execute complete battery of evaluations and persist results."""
    print("=== Starting Sewa Setu Multi-Persona Evaluations ===")
    overall_start = time.time()
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_evaluated": 0,
        "passed": 0,
        "failed": 0,
        "pass_rate_pct": 0.0,
        "duration_seconds": 0.0,
        "citizen_evaluations": [],
        "officer_evaluations": [],
    }

    # Evaluate all 10 citizen personas
    print("\n--- Evaluating Citizen Personas ---")
    for persona in PERSONAS:
        print(f"Evaluating {persona['name']} ({persona['id']})...", end=" ", flush=True)
        res = await evaluate_persona(persona, citizen_url)
        status_str = "PASS" if res["passed"] else "FAIL"
        print(f"[{status_str}] ({res['duration_ms']}ms)")
        results["citizen_evaluations"].append(res)
        results["total_evaluated"] += 1
        if res["passed"]:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Evaluate officer personas
    print("\n--- Evaluating Officer Personas ---")
    for officer in OFFICER_PERSONAS:
        print(f"Evaluating {officer['name']} ({officer['id']})...", end=" ", flush=True)
        res = await evaluate_officer(officer, officer_url)
        status_str = "PASS" if res["passed"] else "FAIL"
        print(f"[{status_str}] ({res['duration_ms']}ms)")
        results["officer_evaluations"].append(res)
        results["total_evaluated"] += 1
        if res["passed"]:
            results["passed"] += 1
        else:
            results["failed"] += 1

    overall_duration = round(time.time() - overall_start, 2)
    results["duration_seconds"] = overall_duration
    if results["total_evaluated"] > 0:
        results["pass_rate_pct"] = round((results["passed"] / results["total_evaluated"]) * 100, 1)

    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n=== Evaluation Run Complete ===")
    print(f"Total: {results['total_evaluated']} | Passed: {results['passed']} | Failed: {results['failed']} | Rate: {results['pass_rate_pct']}% | Time: {overall_duration}s")
    print(f"Results saved to: {RESULTS_FILE}")
    return results


if __name__ == "__main__":
    c_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001/mcp"
    o_url = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8002/mcp"
    asyncio.run(run_all_evaluations(c_url, o_url))
