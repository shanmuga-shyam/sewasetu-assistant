# -*- coding: utf-8 -*-
"""
Officer MCP Server — Sewa Setu Old Age Pension Portal.
Streamable HTTP server for Block Officers and Departmental Administrators.
Restricted exclusively to officer scope and authenticated officer username.
"""

import os
import sys
from datetime import datetime, timedelta

# Path configuration
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from mcp.server.mcpserver import MCPServer
import app as portal
from mcp_servers.auth import get_current_user, MCPAuthMiddleware

# Initialize MCPServer instance
officer_mcp = MCPServer(
    name="sewasetu-officer",
    instructions=(
        "You are the Sewa Setu Block Officer Assistant. You assist block-level approving officers "
        "and social welfare administrators in Purvanchal to review the application queue, inspect applicant files, "
        "verify documents, and record approval or rejection decisions with full statutory audit logging. "
        "Applications must be decided within the statutory 15-day SLA to avoid automatic deemed approval."
    ),
)


@officer_mcp.tool()
def list_applications(
    status: str = "PENDING",
    block: str = None,
    page: int = 1,
    limit: int = 50,
    overdue_only: bool = False,
) -> dict:
    """
    List applications in the department queue with optional filtering.
    
    Args:
        status: Application status to filter ('PENDING', 'APPROVED', 'REJECTED', 'DEEMED_APPROVED', 'WITHDRAWN', or 'ALL').
        block: Optional block filter (e.g. 'Sonari', 'Rajapara', 'Namti').
        page: Page number (1-indexed, default 1).
        limit: Number of items per page (default 50, max 100).
        overdue_only: If True, returns only applications pending beyond the 15-day statutory SLA.
        
    Returns:
        Dictionary containing matching applications, pagination info, and summary counts.
    """
    limit = max(1, min(limit, 100))
    page = max(1, page)
    offset = (page - 1) * limit

    conn = portal.get_db()
    cur = conn.cursor()
    try:
        where_clauses = []
        params = []

        if status.upper() != "ALL":
            where_clauses.append("status = %s")
            params.append(status.upper())

        if block and block.strip():
            where_clauses.append("block = %s")
            params.append(block.strip())

        if overdue_only:
            sla_cutoff = portal.now_ist() - timedelta(days=portal.SLA_DAYS)
            where_clauses.append("status = 'PENDING' AND submitted_at < %s")
            params.append(sla_cutoff)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Get total count
        cur.execute(f"SELECT count(*) FROM applications {where_sql}", params)
        total_count = cur.fetchone()[0]

        # Get records
        cur.execute(
            f"""SELECT id, application_no, applicant_name, mobile, block, village, status, submitted_at, dob
               FROM applications
               {where_sql}
               ORDER BY submitted_at ASC
               LIMIT %s OFFSET %s""",
            params + [limit, offset],
        )
        rows = cur.fetchall()

        now = portal.now_ist()
        applications = []
        for r in rows:
            app_id, app_no, name, mob, blk, vil, stat, sub_at, dob = r
            days_pending = (now - sub_at).days if sub_at else 0
            is_overdue = (days_pending >= portal.SLA_DAYS) and (stat == "PENDING")
            age = portal.age_on(dob, now.date()) if dob else None

            applications.append({
                "application_id": app_id,
                "application_no": app_no,
                "applicant_name": name,
                "mobile": mob,
                "block": blk,
                "village": vil,
                "status": stat,
                "submitted_at": sub_at.strftime("%Y-%m-%d %H:%M:%S") if sub_at else None,
                "age": age,
                "days_pending": days_pending,
                "overdue": is_overdue,
            })

        return {
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 1,
            "filter_status": status,
            "filter_block": block,
            "filter_overdue_only": overdue_only,
            "applications": applications,
        }
    finally:
        cur.close()
        conn.close()


@officer_mcp.tool()
def get_application_details(application_id: int = None, application_no: str = None) -> dict:
    """
    Retrieve full dossier for an application, including applicant details, bank account,
    age calculation, document path, and complete audit trail.
    
    Args:
        application_id: Primary key ID of the application.
        application_no: Application reference number (e.g. 'SSP26123456').
        
    Returns:
        Comprehensive application dossier.
    """
    if application_id is None and not application_no:
        return {"found": False, "message": "Either application_id or application_no must be provided."}

    conn = portal.get_db()
    cur = conn.cursor()
    try:
        if application_id is not None:
            cur.execute(
                """SELECT id, application_no, applicant_name, mobile, dob, gender,
                          marital_status, husband_name, village, block, bank_account,
                          ifsc, doc_path, status, submitted_at, decided_at, decided_by
                   FROM applications WHERE id = %s""",
                (application_id,),
            )
        else:
            cur.execute(
                """SELECT id, application_no, applicant_name, mobile, dob, gender,
                          marital_status, husband_name, village, block, bank_account,
                          ifsc, doc_path, status, submitted_at, decided_at, decided_by
                   FROM applications WHERE application_no = %s""",
                (application_no.strip(),),
            )

        row = cur.fetchone()
        if not row:
            return {"found": False, "message": "Application not found."}

        app_id, app_no, name, mob, dob, gender, m_status, h_name, vil, blk, acct, ifsc, doc_path, stat, sub_at, dec_at, dec_by = row

        now = portal.now_ist()
        age = portal.age_on(dob, now.date()) if dob else None
        days_pending = (now - sub_at).days if sub_at else 0
        is_overdue = (days_pending >= portal.SLA_DAYS) and (stat == "PENDING")

        # Fetch audit log
        cur.execute(
            "SELECT action, actor, note, at FROM audit_log WHERE application_id = %s ORDER BY at ASC",
            (app_id,),
        )
        audit_rows = cur.fetchall()
        audit_trail = [
            {
                "action": a[0],
                "actor": a[1],
                "note": a[2] or "",
                "timestamp": a[3].strftime("%Y-%m-%d %H:%M:%S") if a[3] else None,
            }
            for a in audit_rows
        ]

        doc_exists = os.path.exists(doc_path) if doc_path else False

        return {
            "found": True,
            "application_id": app_id,
            "application_no": app_no,
            "applicant_name": name,
            "mobile": mob,
            "dob": dob.strftime("%d/%m/%Y") if dob else None,
            "age": age,
            "gender": gender,
            "marital_status": m_status,
            "husband_name": h_name,
            "village": vil,
            "block": blk,
            "bank_account": acct,
            "ifsc": ifsc,
            "doc_path": doc_path,
            "doc_exists": doc_exists,
            "status": stat,
            "submitted_at": sub_at.strftime("%Y-%m-%d %H:%M:%S") if sub_at else None,
            "decided_at": dec_at.strftime("%Y-%m-%d %H:%M:%S") if dec_at else None,
            "decided_by": dec_by,
            "days_pending": days_pending,
            "is_overdue": is_overdue,
            "audit_trail": audit_trail,
        }
    finally:
        cur.close()
        conn.close()


@officer_mcp.tool()
def review_application_document(application_id: int) -> dict:
    """
    Inspect the age proof document uploaded for an application.
    
    Args:
        application_id: Application ID.
        
    Returns:
        Document file metadata, verification status, and snippet/details.
    """
    conn = portal.get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT application_no, applicant_name, doc_path, dob, block FROM applications WHERE id = %s", (application_id,))
        row = cur.fetchone()
        if not row:
            return {"found": False, "message": "Application not found."}

        app_no, name, doc_path, dob, blk = row

        if not doc_path:
            return {
                "found": True,
                "has_document": False,
                "message": "No document path associated with this application.",
            }

        exists = os.path.exists(doc_path)
        file_size = os.path.getsize(doc_path) if exists else 0
        filename = os.path.basename(doc_path)

        preview = "Document file present on disk and readable." if exists else "File not present on server disk."
        if exists:
            try:
                with open(doc_path, "r", errors="ignore") as f:
                    snippet = f.read(200)
                    if snippet.strip():
                        preview = snippet.strip()
            except Exception:
                pass

        return {
            "found": True,
            "has_document": True,
            "application_id": application_id,
            "application_no": app_no,
            "applicant_name": name,
            "filename": filename,
            "doc_path": doc_path,
            "file_exists": exists,
            "file_size_bytes": file_size,
            "preview_snippet": preview,
            "declared_dob": dob.strftime("%d/%m/%Y") if dob else None,
            "block": blk,
        }
    finally:
        cur.close()
        conn.close()


@officer_mcp.tool()
def approve_application(application_id: int, justification: str) -> dict:
    """
    Approve a pending pension application.
    Stamps the approving officer's username and mandatory audit note into the database.
    Sends confirmation SMS to the citizen.
    
    Args:
        application_id: Application ID to approve.
        justification: Mandatory justification/audit note for why the application is approved.
        
    Returns:
        Approval confirmation with updated status and audit details.
    """
    user = get_current_user()
    officer_name = user["username"]

    clean_justification = (justification or "").strip()
    if not clean_justification:
        return {
            "success": False,
            "message": "A justification note is required to approve an application. Please state the reason for approval.",
        }

    conn = portal.get_db()
    cur = conn.cursor()
    try:
        # Check current status
        cur.execute("SELECT application_no, mobile, status FROM applications WHERE id = %s", (application_id,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "message": "Application not found."}

        app_no, mobile, current_status = row
        if current_status != "PENDING":
            return {
                "success": False,
                "message": f"Cannot approve application {app_no}. Current status is '{current_status}'. Only PENDING applications can be approved.",
            }

        now = portal.now_ist()
        cur.execute(
            """UPDATE applications
               SET status = 'APPROVED', decided_at = %s, decided_by = %s
               WHERE id = %s AND status = 'PENDING'
               RETURNING application_no""",
            (now, f"officer:{officer_name}", application_id),
        )
        updated = cur.fetchone()
        if not updated:
            conn.rollback()
            return {"success": False, "message": "Concurrent modification; application could not be approved."}

        portal.write_audit(
            cur,
            application_id,
            "APPROVED",
            f"officer:{officer_name}",
            clean_justification,
        )
        conn.commit()

        # Send approval SMS to citizen
        portal.send_sms(
            mobile,
            f"Sewa Setu: your pension application {app_no} has been APPROVED by Social Welfare Officer {officer_name}.",
        )

        return {
            "success": True,
            "application_id": application_id,
            "application_no": app_no,
            "status": "APPROVED",
            "decided_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "decided_by": f"officer:{officer_name}",
            "justification": clean_justification,
            "message": f"Application {app_no} has been successfully approved.",
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        cur.close()
        conn.close()


@officer_mcp.tool()
def reject_application(application_id: int, reason: str) -> dict:
    """
    Reject a pending pension application with a recorded reason.
    Stamps the rejecting officer's username and reason into the audit trail.
    Sends rejection SMS notice to the applicant.
    
    Args:
        application_id: Application ID to reject.
        reason: Mandatory specific reason for rejection (e.g. invalid document, age discrepancy, outside jurisdiction).
        
    Returns:
        Rejection confirmation with audit details.
    """
    user = get_current_user()
    officer_name = user["username"]

    clean_reason = (reason or "").strip()
    if not clean_reason:
        return {
            "success": False,
            "message": "A specific rejection reason is mandatory. Please record the statutory reason for rejection.",
        }

    conn = portal.get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT application_no, mobile, status FROM applications WHERE id = %s", (application_id,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "message": "Application not found."}

        app_no, mobile, current_status = row
        if current_status != "PENDING":
            return {
                "success": False,
                "message": f"Cannot reject application {app_no}. Current status is '{current_status}'. Only PENDING applications can be rejected.",
            }

        now = portal.now_ist()
        cur.execute(
            """UPDATE applications
               SET status = 'REJECTED', decided_at = %s, decided_by = %s
               WHERE id = %s AND status = 'PENDING'
               RETURNING application_no""",
            (now, f"officer:{officer_name}", application_id),
        )
        updated = cur.fetchone()
        if not updated:
            conn.rollback()
            return {"success": False, "message": "Concurrent modification; application could not be rejected."}

        portal.write_audit(
            cur,
            application_id,
            "REJECTED",
            f"officer:{officer_name}",
            clean_reason,
        )
        conn.commit()

        # Send rejection SMS to citizen
        portal.send_sms(
            mobile,
            f"Sewa Setu: pension application {app_no} was not approved. Reason: {clean_reason}",
        )

        return {
            "success": True,
            "application_id": application_id,
            "application_no": app_no,
            "status": "REJECTED",
            "decided_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "decided_by": f"officer:{officer_name}",
            "rejection_reason": clean_reason,
            "message": f"Application {app_no} has been rejected.",
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        cur.close()
        conn.close()


@officer_mcp.tool()
def get_block_statistics() -> dict:
    """
    Get high-level statistics across all blocks, including status distribution,
    pending queues, SLA overdue counts, and deemed approval counts.
    """
    conn = portal.get_db()
    cur = conn.cursor()
    try:
        # Distribution by status
        cur.execute("SELECT status, count(*) FROM applications GROUP BY status ORDER BY count(*) DESC")
        status_counts = dict(cur.fetchall())

        # Overdue count (> 15 days)
        sla_cutoff = portal.now_ist() - timedelta(days=portal.SLA_DAYS)
        cur.execute("SELECT count(*) FROM applications WHERE status = 'PENDING' AND submitted_at < %s", (sla_cutoff,))
        overdue_count = cur.fetchone()[0]

        # Breakdown by block for pending
        cur.execute(
            """SELECT block, count(*) FROM applications
               WHERE status = 'PENDING'
               GROUP BY block ORDER BY count(*) DESC"""
        )
        pending_by_block = dict(cur.fetchall())

        # Total applications
        cur.execute("SELECT count(*) FROM applications")
        total = cur.fetchone()[0]

        return {
            "total_applications": total,
            "status_distribution": status_counts,
            "sla_overdue_pending": overdue_count,
            "statutory_sla_days": portal.SLA_DAYS,
            "pending_by_block": pending_by_block,
            "deemed_approved_count": status_counts.get("DEEMED_APPROVED", 0),
            "approved_count": status_counts.get("APPROVED", 0),
            "pending_count": status_counts.get("PENDING", 0),
            "rejected_count": status_counts.get("REJECTED", 0),
            "withdrawn_count": status_counts.get("WITHDRAWN", 0),
        }
    finally:
        cur.close()
        conn.close()


@officer_mcp.tool()
def search_applications(query: str, search_type: str = "all") -> dict:
    """
    Search applications by mobile number, application number, or applicant name.
    
    Args:
        query: Search term (mobile digits, application number, or name).
        search_type: 'all', 'mobile', 'app_no', or 'name'.
        
    Returns:
        List of matching applications.
    """
    clean_q = query.strip()
    if not clean_q:
        return {"results": [], "total_found": 0}

    conn = portal.get_db()
    cur = conn.cursor()
    try:
        sql = """SELECT id, application_no, applicant_name, mobile, block, status, submitted_at
                 FROM applications WHERE """
        params = []

        if search_type == "mobile" or (clean_q.isdigit() and len(clean_q) == 10):
            sql += "mobile = %s"
            params.append(clean_q)
        elif search_type == "app_no" or clean_q.upper().startswith("SSP"):
            sql += "application_no = %s"
            params.append(clean_q.upper())
        elif search_type == "name":
            sql += "applicant_name ILIKE %s"
            params.append(f"%{clean_q}%")
        else:
            sql += "(mobile = %s OR application_no = %s OR applicant_name ILIKE %s)"
            params.extend([clean_q, clean_q.upper(), f"%{clean_q}%"])

        sql += " ORDER BY submitted_at DESC LIMIT 20"
        cur.execute(sql, params)
        rows = cur.fetchall()

        results = [
            {
                "application_id": r[0],
                "application_no": r[1],
                "applicant_name": r[2],
                "mobile": r[3],
                "block": r[4],
                "status": r[5],
                "submitted_at": r[6].strftime("%Y-%m-%d %H:%M:%S") if r[6] else None,
            }
            for r in rows
        ]

        return {"results": results, "total_found": len(results), "query": clean_q}
    finally:
        cur.close()
        conn.close()


def create_officer_app():
    """Create Starlette ASGI application with authentication middleware."""
    app = officer_mcp.streamable_http_app()
    app.add_middleware(
        MCPAuthMiddleware,
        expected_role="officer",
        expected_scope="officer",
        server_name="sewasetu-officer-mcp",
    )
    return app


if __name__ == "__main__":
    import uvicorn
    app = create_officer_app()
    port = int(os.environ.get("OFFICER_MCP_PORT", 8002))
    print(f"Starting Officer MCP Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
