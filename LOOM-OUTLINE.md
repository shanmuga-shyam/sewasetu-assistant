# Loom Video Walkthrough Outline (3-Minute Script & Visuals)

**Target Duration:** Exactly 3 minutes (180 seconds)  
**Format:** Face & Screen (Webcam in corner, active screen demo)  
**Audience:** Director, Department of Social Welfare, Government of Purvanchal  
**Presenter:** Bharat Digital Fellow  

---

## Storyboard & Timing Breakdown

```
[0:00 - 0:30]  Hook & Achievement Overview (Face + Portal Screen)
[0:30 - 1:15]  Dual MCP Architecture & Security Isolation (Terminal & Code)
[1:15 - 2:05]  Interactive Personas & Live Evaluation Walkthrough (/eval-dashboard)
[2:05 - 2:40]  Database Verification & System of Record Proof (psql & Admin View)
[2:40 - 3:00]  Key Learnings & Summary (Face to Camera)
```

---

## Detailed Script & Visual Cues

### [0:00 – 0:30] Hook & What Was Achieved
- **Visual:** Face in circle; screen showing the Sewa Setu Portal homepage (`http://localhost:8000`) and the audio note transcript.
- **Spoken Script:**
  > *"Namaskar Director Sahab. Last month, a 70-year-old grandmother in Sonari had to travel to the block counter because AI assistants couldn't talk to our pension portal. Today, I am proud to present Sewa Setu Assistant—the official Model Context Protocol integration for Purvanchal's Old Age Pension Scheme.*
  > 
  > *We have built two dedicated MCP servers over Streamable HTTP: one for citizens and one for block officers. The portal remains the single system of record, with zero compromise on scheme rules, statutory SLAs, or audit logging."*

### [0:30 – 1:15] Dual MCP Architecture & Security Isolation
- **Visual:** Switch screen to code / terminal showing `citizen_server.py` and `officer_server.py`, highlighting the two endpoints on ports `8001` and `8002`.
- **Spoken Script:**
  > *"To solve the security and hallucination concerns your IT team raised, we made two critical architectural choices:*
  > 
  > *First, strict protocol separation. A citizen's assistant connecting to `/mcp/citizen` cannot even see the officer's approval tools in its schema. Tool discovery is physically isolated.*
  > 
  > *Second, immutable context binding. The citizen assistant never asks for or handles OTPs or passwords. It connects via OAuth 2.1 with RS256 Bearer tokens, and the applicant's mobile number is bound directly from the cryptographic token. The AI assistant cannot forge or spoof another citizen's identity.*
  > 
  > *Meanwhile, on `/mcp/officer`, any approval or rejection automatically stamps the officer's name and mandatory statutory justification directly into the audit log."*

### [1:15 – 2:05] Synthetic Personas & Live Evaluation Walkthrough
- **Visual:** Switch screen to the live **`/eval-dashboard`** (`http://localhost:8000/eval-dashboard`). Show the 100% pass rate card, then scroll down to persona cards.
- **Spoken Script:**
  > *"As you requested, we sat at the counter in our heads and created 10 realistic Purvanchal citizen personas plus officer workflows:*
  > 
  > *Here is Phuleswari Saikia, a 71-year-old widow from Derial, applying through her granddaughter Gita. Here is Tarulata Gogoi, who made a typo in her bank account, withdrew her pending application via the assistant, and resubmitted cleanly.*
  > 
  > *Here is Ramakant Tewari, an underage applicant of 58, who was politely rejected because our MCP tools enforce the statutory 60-year rule without exception.*
  > 
  > *And here is Minati Barua, whose application waited 22 days—the assistant informed her of her legal rights under the Purvanchal Right to Public Services Act for automatic deemed approval.*
  > 
  > *We test them not with mocks, but with a real MCP client establishing live HTTP sessions."*

### [2:05 – 2:40] Database Verification & The Portal as System of Record
- **Visual:** Click into Phuleswari's conversation transcript on `/eval-dashboard`, showing the database assertion table. Switch tab to `/admin/applications` showing Phuleswari's application in the departmental queue, then approved by BDO Sonari.
- **Spoken Script:**
  > *"Look at the database verification table right here: every interaction checks PostgreSQL directly. When Phuleswari applied via the AI assistant, row `100012` was inserted in `applications`, her status portal account was provisioned with her DOB as password, and an SMS was dispatched via the gateway.*
  > 
  > *Then, BDO Anurag Sharma connected his officer assistant, inspected her age proof, and approved her pension. If we check the portal admin dashboard right now, Phuleswari's application is right there, marked APPROVED by `officer:bdo_sonari` with full audit trail.*
  > 
  > *Counter, kiosk, or AI assistant—they all share the exact same system of record."*

### [2:40 – 3:00] What We Learned & Conclusion
- **Visual:** Full face camera or screen showing `/eval-dashboard` summary metrics.
- **Spoken Script:**
  > *"What did we learn? First, that AI in governance should not replace the portal—it should be an empathetic voice on top of deterministic rules. And second, that elderly citizens need the freedom to withdraw and correct mistakes easily without fear.*
  > 
  > *The system is fully tested, containerized with Docker Compose, and ready for your team to test with Claude Code. Thank you."*

---

## Presenter Checklist Before Recording
- [ ] Ensure local PostgreSQL, SMS Gateway, Citizen MCP (8001), Officer MCP (8002), and Portal (8000) are running.
- [ ] Have browser tabs open:
  1. `http://localhost:8000` (Portal Home)
  2. `http://localhost:8000/eval-dashboard` (Evaluation Dashboard with 100% pass results)
  3. `http://localhost:8000/admin` (Departmental admin list showing applications)
- [ ] Practice the script against a 3-minute stopwatch.
