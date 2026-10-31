# Design Note: Sewa Setu Old Age Pension Assistant

**Author:** Bharat Digital Fellow  
**Scheme:** Old Age Pension Scheme (Rs. 250/month, Purvanchal Department of Social Welfare)  
**System:** Sewa Setu Portal & Dual MCP Agent Architecture

---

## The Three Decisions That Mattered Most

### 1. Strict Physical and Protocol Separation of Citizen and Officer Endpoints with Context Binding
The Director’s primary instruction was unambiguous: *"Two MCP servers over streamable HTTP: one for applicants, one for the block officer. Separate endpoints; a citizen's assistant should not even see the officer's tools."*

We rejected the naive pattern of deploying a single unified MCP server with runtime tool-filtering flags. Instead, we implemented two separate ASGI applications running on distinct endpoints (`/mcp/citizen` on port 8001 and `/mcp/officer` on port 8002):
- **Zero Tool Discovery Leakage:** A citizen’s assistant querying `tools/list` receives only citizen tools (`check_eligibility`, `get_my_application`, `submit_pension_application`, `withdraw_my_application`, `get_application_acknowledgment`, `check_sla_timeline`). The officer decision tools (`approve_application`, `reject_application`, `list_applications`) are physically absent from the schema.
- **Immutable Context Binding via OAuth Token:** Crucially, tools like `submit_pension_application` or `withdraw_my_application` **do not accept a mobile number parameter**. The applicant’s identity is bound directly from the RS256 JWT claims (`sub: citizen:<mobile>`) via request-scoped `ContextVar`. An AI agent cannot accidentally or maliciously spoof another citizen's mobile.
- **Officer Audit Accountability:** For block officers, the approving officer’s username is extracted directly from `sub: officer:<username>` and recorded alongside a mandatory statutory justification note in the PostgreSQL `audit_log`.

### 2. The Portal as the Invariable System of Record with Shared Business Logic
In government service delivery, AI assistants must never become a parallel bureaucracy with divergent rules. As the Director emphasized: *"The portal remains the system of record. An AI assistant is just another way to apply following the same rules and validations as the portal... An application made from either place must be visible in both."*

We architected the MCP server tools to call the exact same core functions in `app/app.py`:
- `validate_application()`: strictly enforces minimum age (60+), the 6 designated pilot blocks (Sonari, Rajapara, Dhemaji Pathar, Borgaon, Namti, Khelua), 9–18 digit bank account format, 11-character IFSC format, and age proof document presence.
- `active_application()`: guarantees that no mobile number can hold more than one active application (`PENDING`, `APPROVED`, `DEEMED_APPROVED`).
- `create_application()`: atomically provisions the citizen’s status portal account (with date of birth as password) and dispatches confirmation notifications via the SMS gateway.
- An application filed via Claude Code on a mobile phone in Sonari block is immediately visible on the BDO’s web dashboard and searchable by status or mobile number.

### 3. Actual MCP Streamable HTTP Client Evaluations Backed by Live Database State Checks
Rather than writing synthetic mock tests that simulate function returns, we constructed an evaluation framework (`mcp_client_evaluator.py`) that executes bona fide MCP client sessions:
- The evaluator opens streamable HTTP sessions using `mcp.client.streamable_http`, sends RS256 Bearer tokens, initializes the protocol, and conducts multi-turn dialogues across **10 realistic synthetic citizen personas** and **2 officer personas**.
- After every interaction, the evaluator inspects the actual PostgreSQL database tables (`applications`, `portal_users`, `audit_log`) to verify the state transitions (e.g., verifying that Tarulata's first application was updated to `WITHDRAWN` by `APPLICANT` before her corrected application was saved as `PENDING`).
- Real-time results, multi-turn transcripts, and database verification queries are served on the interactive **`/eval-dashboard`** on the live deployment.

---

## The One Decision We Would Make Differently With More Time

### Embedded Client-Side OCR & Document Validation Before Queue Submission
Currently, when an applicant submits an age-proof document through the AI assistant, the file is saved to the upload store and validated for existence, size, and extension, while the actual verification of whether the document matches the claimed DOB is left to the block officer's queue review.

With more time, we would integrate an in-process optical character recognition (OCR) / vision-language model pipeline directly into the Citizen MCP server's `check_eligibility` and `submit_pension_application` flow. 

When an elderly citizen or kiosk operator uploads an Aadhaar or Voter ID image, the assistant would extract the printed date of birth and name, cross-check them against the form inputs, and immediately warn the citizen: *"Your Aadhaar card shows birth year 1968 (age 58), which does not match your claimed age of 71."* 

Catching document discrepancies at the moment of conversation—rather than 10 days later when an officer rejects the case—would dramatically reduce rejection churn and relieve administrative backlog for block officers.
