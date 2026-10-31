# Sewa Setu — Old Age Pension Portal & MCP Agent Integration

Department of Social Welfare, Government of Purvanchal.

Sewa Setu provides old age pensions (Rs. 250/month) to eligible residents aged 60 and above across Purvanchal. This repository contains the complete portal, the PostgreSQL database with 100k production records, the simulated SMS gateway, and **two Model Context Protocol (MCP) servers over streamable HTTP** enabling AI assistants (such as Claude Code) to act on behalf of citizens and block officers under strict OAuth 2.1 authorization.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |       Claude Code / AI Client         |
                      +---------------------------------------+
                                  |                 |
     OAuth Token: scope `citizen` |                 | OAuth Token: scope `officer`
                                  v                 v
                 +-------------------+   +--------------------+
                 |    Citizen MCP    |   |    Officer MCP     |
                 |  Streamable HTTP  |   |  Streamable HTTP   |
                 |     Port 8001     |   |     Port 8002      |
                 +-------------------+   +--------------------+
                           \                       /
                            \                     /
                             v                   v
                 +--------------------------------------------+
                 |       Sewa Setu Portal (Flask / App)       |
                 |         Port 8000 (System of Record)       |
                 |  - OAuth 2.1 Auth Server (PKCE / RS256)    |
                 |  - Web Application & Status Check          |
                 |  - /eval-dashboard (Multi-Persona Evals)   |
                 |  - Streamable HTTP Reverse Proxies         |
                 +--------------------------------------------+
                             /          |          \
                            /           |           \
                           v            v            v
                 +------------+   +-----------+   +----------+
                 | PostgreSQL |   | SMS GW    |   | Nightly  |
                 | Database   |   | Port 8025 |   | RTPS SLA |
                 | (100k seed)|   |           |   | Cron     |
                 +------------+   +-----------+   +----------+
```

---

## Quick Start: Running with Docker Compose

To start all services (Postgres, Portal, Citizen MCP, Officer MCP, SMS Gateway, Nightly Cron):

```bash
ADMIN_PASSWORD=pick-something docker compose up --build
```

### Endpoints
- **Public Portal**: http://localhost:8000
- **Evaluation Dashboard**: http://localhost:8000/eval-dashboard
- **Citizen Status Portal**: http://localhost:8000/status (Mobile + password: DOB as `DDMMYYYY`)
- **Departmental Officer Login**: http://localhost:8000/admin (User: `admin`, Password: `${ADMIN_PASSWORD}`)
- **Citizen MCP Server (Streamable HTTP)**:
  - Direct: `http://localhost:8001/mcp`
  - Via Portal Proxy: `http://localhost:8000/mcp/citizen`
- **Officer MCP Server (Streamable HTTP)**:
  - Direct: `http://localhost:8002/mcp`
  - Via Portal Proxy: `http://localhost:8000/mcp/officer`
- **OAuth Discovery (RFC 8414)**: `http://localhost:8000/.well-known/oauth-authorization-server`
- **JWKS Public Key (RFC 7517)**: `http://localhost:8000/.well-known/jwks.json`
- **Simulated SMS Gateway Console**: `http://localhost:8000/__gateway/` or `http://localhost:8025/`

---

## Running Locally (Without Docker)

1. **Activate Virtual Environment**:
   ```bash
   source .venv/bin/activate
   pip install -r app/requirements.txt
   ```

2. **Start PostgreSQL & Load Data**:
   Ensure PostgreSQL is running on port 5432 with database `sewasetu` and user `sewasetu`.
   ```bash
   psql -U sewasetu -h localhost -d sewasetu -f app/schema.sql
   psql -U sewasetu -h localhost -d sewasetu -f seed/seed.sql
   ```

3. **Start Simulated SMS Gateway**:
   ```bash
   python smsgw/app.py
   ```

4. **Start Citizen and Officer MCP Servers**:
   ```bash
   # Terminal 1: Citizen MCP
   CITIZEN_MCP_PORT=8001 python app/mcp_servers/citizen_server.py

   # Terminal 2: Officer MCP
   OFFICER_MCP_PORT=8002 python app/mcp_servers/officer_server.py
   ```

5. **Start Portal Web App**:
   ```bash
   # Terminal 3: Flask Portal
   DB_HOST=localhost DB_PORT=5432 DB_USER=sewasetu DB_PASSWORD=sewasetu123 DB_NAME=sewasetu \
   SMS_GATEWAY_URL=http://localhost:8025 \
   CITIZEN_MCP_URL=http://localhost:8001/mcp OFFICER_MCP_URL=http://localhost:8002/mcp \
   ADMIN_USERNAME=admin ADMIN_PASSWORD=adminpass python app/app.py
   ```

---

## MCP Server Tools & Boundaries

### 1. Citizen MCP Server (`sewasetu-citizen`)
Exclusively accessible with OAuth tokens carrying `role: citizen` and `scope: citizen`. The authenticated citizen's mobile number is strictly extracted from the token subject (`citizen:<mobile>`).

| Tool Name | Parameters | Purpose |
|---|---|---|
| `check_eligibility` | `age: int`, `dob: str`, `block: str` | Verifies age (60+) and pilot block eligibility (Sonari, Rajapara, Dhemaji Pathar, Borgaon, Namti, Khelua). Returns scheme details (Rs. 250/mo, 15-day SLA). |
| `get_my_application` | None | Retrieves applicant's current active application, status, bank account (masked), and full audit trail. |
| `submit_pension_application` | `applicant_name`, `dob`, `gender`, `marital_status`, `village`, `block`, `bank_account`, `ifsc`, `age_proof_doc_name` | Submits a new pension application. Enforces scheme validations, checks for duplicate active application, writes to `applications`, `portal_users`, and `audit_log`, and triggers SMS. |
| `withdraw_my_application` | None | Allows the citizen to cancel an application with mistakes while in `PENDING` state to permit reapplying afresh. |
| `get_application_acknowledgment` | None | Retrieves computer-generated acknowledgment details and PDF slip URL (`/ack/<id>.pdf`). |
| `check_sla_timeline` | None | Tracks days elapsed against the statutory 15-day processing SLA under the Purvanchal Right to Public Services (RTPS) Act. Flags deemed approval eligibility. |

### 2. Officer MCP Server (`sewasetu-officer`)
Exclusively accessible with OAuth tokens carrying `role: officer` and `scope: officer`. Approving actions automatically stamp the officer's identity into the database audit log.

| Tool Name | Parameters | Purpose |
|---|---|---|
| `list_applications` | `status`, `block`, `page`, `limit`, `overdue_only` | Lists pending/processed applications with queue metrics and SLA overdue flags. |
| `get_application_details` | `application_id`, `application_no` | Returns full applicant file, age verification, address, bank details, and full statutory audit trail. |
| `review_application_document` | `application_id` | Verifies uploaded age proof file existence, format, and content on disk. |
| `approve_application` | `application_id`, `justification` | Records statutory approval decision with mandatory justification note, sets status to `APPROVED`, writes to audit log, and notifies citizen via SMS. |
| `reject_application` | `application_id`, `reason` | Records statutory rejection decision with mandatory reason note, sets status to `REJECTED`, writes to audit log, and notifies citizen via SMS. |
| `get_block_statistics` | None | Aggregates application counts, status breakdowns, pending queues, and overdue SLA counts across all 6 blocks. |
| `search_applications` | `query`, `search_type` | Searches applications by mobile number, application reference number, or applicant name. |

---

## Security & Access Control

1. **Strict Boundary Isolation**:
   - Citizen assistant cannot see or execute officer tools (`approve_application`, `reject_application`, `list_applications` are not present on Citizen MCP).
   - Officer assistant cannot apply on behalf of a citizen without citizen consent.
2. **Cryptographic OAuth 2.1 Verification**:
   - Access tokens are RS256-signed JWTs verified against portal public keys at `/.well-known/jwks.json`.
   - Audience indicator enforcement (RFC 8707).
   - Session limits: 2-hour hard session for citizens; 8-hour session for block officers.
   - Unauthorized or expired tokens are immediately rejected with HTTP `401 Unauthorized` and `WWW-Authenticate` header.
3. **Cross-Citizen Isolation**:
   - The citizen's assistant is strictly bound to `citizen:<mobile>` from token claims.
   - Assistant cannot access, modify, or withdraw applications belonging to other mobile numbers.

---

## Synthetic Personas & Multi-Turn Evaluations

To test real-world scenarios, 10 realistic citizen personas reflecting Purvanchal's elderly population, regional dialects, and administrative edge cases were created and evaluated:

1. **Phuleswari Saikia** (Age 71, Sonari): Elderly widowed grandmother submitting for the first time with granddaughter's help.
2. **Bhabesh Kalita** (Age 64, Rajapara): Direct, impatient daily wager querying the status of his pending submission.
3. **Tarulata Gogoi** (Age 68, Namti): Realizes bank passbook number had a typo; withdraws `PENDING` application and resubmits with clean account.
4. **Ramakant Tewari** (Age 58, Borgaon): Underage farmer; application correctly blocked by age validation threshold (60+).
5. **Minati Barua** (Age 74, Sonari): Application pending 22 days; assistant correctly identifies statutory 15-day SLA lapse and deemed approval rights.
6. **Dimbeswar Chetia** (Age 66, Dhemaji Pathar): Assisted by a CSC kiosk operator; submits and obtains official acknowledgment receipt.
7. **Arati Das** (Age 62, Dispur): Resident outside pilot blocks; submission rejected due to invalid block.
8. **Joyprakash Nath** (Age 65, Khelua): Confusion regarding bank IFSC code formatting; guided to standardized 11-digit uppercase format.
9. **Malati Medhi** (Age 76, Sonari): Illiterate widow querying her approved pension decision and officer remarks.
10. **Jagannath Bora** (Age 63, Namti): Attempts duplicate submission on already active number; blocked by scheme constraint.

### Officer Evaluations:
11. **Anurag Sharma (BDO Sonari)**: Reviews Phuleswari's application, inspects age proof document, and approves with statutory justification.
12. **Priyanka Neog (BDO Rajapara)**: Monitors block statistics and overdue applications older than 15 days.

### Running Evaluations:
```bash
python app/evals/mcp_client_evaluator.py http://127.0.0.1:8001/mcp http://127.0.0.1:8002/mcp
```
Results and full multi-turn conversation transcripts are viewable on the interactive **Evaluation Dashboard** at `/eval-dashboard`.

---

## Automated Test Suite

Execute the full automated test suite covering OAuth PKCE, MCP tool lifecycles, and security boundaries:

```bash
PYTHONPATH=app DB_HOST=localhost DB_PORT=5432 DB_USER=sewasetu DB_PASSWORD=sewasetu123 DB_NAME=sewasetu \
SMS_GATEWAY_URL=http://localhost:8025 python -m unittest discover -s app/tests
```

All 14 unit and integration tests execute and pass in < 0.2s.
