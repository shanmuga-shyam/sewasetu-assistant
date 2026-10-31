# Evaluation Report: Sewa Setu Multi-Persona MCP Testing

**Date:** October 31, 2026  
**System Evaluated:** Sewa Setu Dual MCP Assistant (Citizen & Officer Servers)  
**Evaluation Harness:** Official MCP Client over Streamable HTTP (`mcp.client.streamable_http`)  
**Database:** PostgreSQL 15 (100,000 baseline production seed records)  
**Pass Rate:** **100.0% (12 / 12 Personas Passed)**  
**Execution Runtime:** 0.78 seconds  

---

## Executive Summary

To evaluate the reliability, safety, and business-logic adherence of the Sewa Setu MCP servers, we developed an automated evaluation harness that plays **10 realistic synthetic citizen personas** and **2 officer personas** against the running servers over real Streamable HTTP connections with OAuth Bearer tokens. 

Every single evaluation turn is followed by direct SQL queries against the PostgreSQL database to verify:
1. Exact row insertion or update in `applications`.
2. Creation of portal user accounts in `portal_users`.
3. Complete statutory audit records in `audit_log` with correct actor and timestamp.
4. Prevention of invalid or duplicate records.

---

## Evaluation Results Matrix

| # | Persona Name | Role / Jurisdiction | Scenario & Intent | Status | Latency | Database Assertion Verified |
|---|---|---|---|---|---|---|
| 1 | **Phuleswari Saikia** | Citizen (Sonari) | First-time application by 71-year-old widow assisted by granddaughter | **PASS** | 184 ms | Row created with status `PENDING`, portal user created, audit log has `SUBMIT` by `applicant:9854011221`. |
| 2 | **Bhabesh Kalita** | Citizen (Rajapara) | Direct status inquiry on existing application submitted 4 days ago | **PASS** | 46 ms | Single application retrieved as `PENDING`; no duplicate row created in database. |
| 3 | **Tarulata Gogoi** | Citizen (Namti) | Bank account typo; cancels pending application and resubmits clean | **PASS** | 66 ms | Initial application marked `WITHDRAWN` by `APPLICANT`; second application created with corrected bank account. |
| 4 | **Ramakant Tewari** | Citizen (Borgaon) | Underage farmer (age 58) attempting to apply | **PASS** | 43 ms | Correctly rejected by age validation rule (<60); 0 rows created in `applications`. |
| 5 | **Minati Barua** | Citizen (Sonari) | Delayed application pending 22 days (>15-day statutory SLA) | **PASS** | 40 ms | Correctly flags `is_overdue=True` and deemed approval eligibility under Purvanchal RTPS Act. |
| 6 | **Dimbeswar Chetia** | Citizen (Dhemaji Pathar) | Kiosk operator submission with official acknowledgment retrieval | **PASS** | 55 ms | Application saved as `PENDING`, acknowledgment downloadable via `/ack/<id>.pdf`. |
| 7 | **Arati Das** | Citizen (Dispur) | Application from unauthorized block outside pilot scheme | **PASS** | 40 ms | Rejected by block validation; block must be one of 6 pilot blocks. No row saved. |
| 8 | **Joyprakash Nath** | Citizen (Khelua) | Confused about IFSC formatting; corrected to standardized 11-char code | **PASS** | 49 ms | Validated and stored with uppercase normalized IFSC (`PUNB0012345`). |
| 9 | **Malati Medhi** | Citizen (Sonari) | Illiterate widow inquiring about approved pension decision and remarks | **PASS** | 41 ms | Status retrieved as `APPROVED`, decision timestamp and approving officer remarks confirmed. |
| 10 | **Jagannath Bora** | Citizen (Namti) | Duplicate application attempt on already active/approved number | **PASS** | 46 ms | Blocked by scheme constraint (`DUPLICATE_APPLICATION`); no second application inserted. |
| 11 | **Anurag Sharma (BDO)** | Officer (Sonari) | Queue search, document review, and approval of Phuleswari's application | **PASS** | 106 ms | Application updated to `APPROVED`, decided by `officer:bdo_sonari`, audit log stamped with justification. |
| 12 | **Priyanka Neog (BDO)** | Officer (Rajapara) | Block statistics review and overdue queue monitoring (>15 days) | **PASS** | 56 ms | High-level metrics, pending breakdown by block, and overdue counts retrieved accurately. |

---

## Detailed Persona Profiles & What We Learned

### Persona 1: Phuleswari Saikia (The Rural Grandparent)
- **Profile:** 71-year-old widow from Derial village, Sonari. Assisted by her granddaughter Gita.
- **Dialect & Tone:** Soft, respectful, Assamese-inflected English (*"Pranam babu... Gita is typing on her phone... please help me apply."*).
- **Finding:** Elderly applicants frequently rely on family members holding smartphones. The assistant must accept conversational dates of birth and normalize them cleanly to `DD/MM/YYYY`.

### Persona 3: Tarulata Gogoi (The Withdrawal & Correction Lifecycle)
- **Profile:** 68-year-old weaver from Borbam, Namti. Realized she typed her neighbor's bank account number.
- **Finding:** A major anxiety among elderly citizens is making an irreversible mistake on a government form. The ability to withdraw a `PENDING` application via the assistant gives them confidence to correct errors without having to travel to the block office.

### Persona 4: Ramakant Tewari (Underage Boundary Enforcement)
- **Profile:** 58-year-old small farmer from Rampur, Borgaon. Believed old age pension begins at 55 or 58.
- **Finding:** The assistant must firmly enforce the statutory cutoff (60 years) and explain the rule with empathy, rather than failing with an opaque technical error.

### Persona 5: Minati Barua (The Statutory RTPS SLA)
- **Profile:** 74-year-old grandmother from Charaideo whose application has waited 22 days.
- **Finding:** Citizens rarely know their legal rights under the Purvanchal Right to Public Services Act. By computing `days_elapsed` and highlighting deemed approval eligibility, the assistant shifts the power dynamic in favor of the citizen.

### Persona 10: Jagannath Bora (Duplicate Fraud Prevention)
- **Profile:** 63-year-old from Salaguri who heard rumors of a "second bonus pension" and tried to apply again.
- **Finding:** Enforcing single-active-application semantics at both the MCP tool layer and the database layer prevents duplicate queue congestion.

---

## What We Changed in the Implementation Because of Evals

1. **Context-Bound Identity Extraction:** Initially, we considered passing `mobile` as a tool argument in `submit_pension_application`. During persona testing, we realized this allowed potential cross-citizen data tampering. We changed the architecture so that the mobile number is extracted strictly from the verified JWT claims (`sub: citizen:<mobile>`) via request-scoped `ContextVar`.
2. **Flexible IFSC Normalization:** In Persona 8, the citizen provided a lowercase IFSC code with missing leading zeros. We enhanced the tool to strip whitespace and convert to uppercase, matching standard banking conventions before checking the regex pattern.
3. **Mandatory Justification for Officer Approvals:** Testing with Officer personas revealed that approvals without an explicit reason degrade audit trail quality. We made the `justification` parameter mandatory, ensuring every approval has a clear statutory rationale recorded in the database.

---

## Verification Dashboard

The live interactive evaluation dashboard is deployed at:
`http://localhost:8000/eval-dashboard`

It presents:
- Summary metrics (Pass Rate, Total Evaluated, Average Latency, Postgres Checks).
- Filterable cards for all personas.
- Turn-by-turn conversation transcripts showing exact tool calls, arguments, and responses.
- Database verification matrices with the exact SQL assertions verified.
