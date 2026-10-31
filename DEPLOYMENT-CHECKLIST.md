# Sewa Setu — Production Deployment Checklist

**Project:** Sewa Setu Old Age Pension Portal & Dual MCP Servers  
**Target Environment:** Linux VM (Ubuntu 22.04 / 24.04 LTS)  
**Classification:** Confidential — Department of Social Welfare, Government of Purvanchal  

---

## 1. Environment Configuration

Set the following environment variables in `.env` or the host environment:

| Variable | Required | Production Example | Description |
|---|---|---|---|
| `PUBLIC_BASE_URL` | **Yes** | `https://sewasetu.purvanchal.gov.in` | Canonical public URL. Stamped into OAuth discovery documents and RS256 token `iss` claim. Must be HTTPS. |
| `ADMIN_USERNAME` | **Yes** | `admin` | Departmental officer username. |
| `ADMIN_PASSWORD` | **Yes** | `[Strong-Random-Password-Min-16-Chars]` | Departmental officer admin password. |
| `SECRET_KEY` | **Yes** | `[Random-Hex-64-Chars]` | Flask session encryption key. |
| `CITIZEN_MCP_PORT` | No | `8001` | Internal port for Citizen MCP Server. |
| `OFFICER_MCP_PORT` | No | `8002` | Internal port for Officer MCP Server. |
| `CITIZEN_MCP_URL` | No | `http://mcp-citizen:8001/mcp` | Internal Docker / localhost Citizen MCP address for reverse proxy. |
| `OFFICER_MCP_URL` | No | `http://mcp-officer:8002/mcp` | Internal Docker / localhost Officer MCP address for reverse proxy. |
| `POSTGRES_DB` | Yes | `sewasetu` | Database name. |
| `POSTGRES_USER` | Yes | `sewasetu` | Database user. |
| `POSTGRES_PASSWORD` | Yes | `[Strong-DB-Password]` | Database password. |

---

## 2. Pre-Deployment Security Audit

- [x] **No Default Credentials:** `ADMIN_PASSWORD` and `POSTGRES_PASSWORD` must be explicitly configured before starting public services.
- [x] **HTTPS Termination:** Configure Caddy or Nginx reverse proxy with TLS 1.3 / Let's Encrypt certificates. Plain HTTP should redirect to HTTPS.
- [x] **OAuth Issuer Match:** Ensure `PUBLIC_BASE_URL` exactly matches the domain accessed by clients to avoid token rejection.
- [x] **Streamable HTTP Header Forwarding:** Ensure reverse proxy forwards `Authorization: Bearer <token>`, `Accept: text/event-stream`, and preserves chunked transfer encoding for SSE.
- [x] **CORS Preflight:** Verify that `OPTIONS` requests to `/.well-known/`, `/oauth/`, `/mcp/citizen`, and `/mcp/officer` return `Access-Control-Allow-Origin: *`.

---

## 3. Deployment Steps via Docker Compose

### Step 1: Clone Repository on Server
```bash
git clone <repo-url> sewasetu-assistant
cd sewasetu-assistant
```

### Step 2: Configure Environment
```bash
cat << 'EOF' > .env
PUBLIC_BASE_URL=https://sewasetu.purvanchal.gov.in
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Purvanchal@Welfare2026!
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_DB=sewasetu
POSTGRES_USER=sewasetu
POSTGRES_PASSWORD=sewasetu123
EOF
```

### Step 3: Launch Containers
```bash
docker compose up -d --build
```

### Step 4: Verify Container Health
```bash
docker compose ps
# Expected services running:
# - sewasetu-assistant-db-1
# - sewasetu-assistant-app-1
# - sewasetu-assistant-mcp-citizen-1
# - sewasetu-assistant-mcp-officer-1
# - sewasetu-assistant-scheduler-1
# - sewasetu-assistant-smsgw-1
```

---

## 4. Post-Deployment Verification Checklist

Execute these smoke checks from an external machine:

### 1. OAuth Discovery & Public Keys
```bash
curl -f https://sewasetu.purvanchal.gov.in/.well-known/oauth-authorization-server
curl -f https://sewasetu.purvanchal.gov.in/.well-known/jwks.json
```
*Expected:* HTTP 200 with JSON metadata and RS256 public keys.

### 2. Citizen MCP Server Authentication Boundary
```bash
curl -I -X POST https://sewasetu.purvanchal.gov.in/mcp/citizen
```
*Expected:* `HTTP/1.1 401 Unauthorized` with header `WWW-Authenticate: Bearer realm="SewaSetu", error="invalid_token"`.

### 3. Officer MCP Server Authentication Boundary
```bash
curl -I -X POST https://sewasetu.purvanchal.gov.in/mcp/officer
```
*Expected:* `HTTP/1.1 401 Unauthorized` with header `WWW-Authenticate: Bearer realm="SewaSetu", error="invalid_token"`.

### 4. Interactive Evaluation Dashboard
Open in browser:
`https://sewasetu.purvanchal.gov.in/eval-dashboard`
*Expected:* 100% Pass Rate across 10 Citizen and 2 Officer Personas with full transcripts and database verification proofs.

### 5. Automated Unit & Integration Tests
```bash
docker compose exec app python -m unittest discover -s /app/tests
```
*Expected:* `14 tests ... OK`.

### 6. Nightly Deemed Approval Cron Verification
```bash
docker compose exec scheduler python /app/scripts/deemed_approval.py
```
*Expected:* Execution report showing count of deemed approved applications under Purvanchal RTPS Act.

---

## 5. Submission Manifest for Application Form

1. **Portal URL:** `https://<your-vm-domain>` (or `http://<vm-ip>:8000`)
2. **Citizen MCP Endpoint:** `https://<your-vm-domain>/mcp/citizen` (or `http://<vm-ip>:8001/mcp`)
3. **Officer MCP Endpoint:** `https://<your-vm-domain>/mcp/officer` (or `http://<vm-ip>:8002/mcp`)
4. **Officer Login Credentials:**
   - Username: `admin`
   - Password: `${ADMIN_PASSWORD}`
5. **Evaluation Dashboard URL:** `https://<your-vm-domain>/eval-dashboard`
6. **Loom Video URL:** (3-minute link as scripted in `LOOM-OUTLINE.md`)
7. **Design Note:** Included in repository as `DESIGN-NOTE.md`
8. **Evaluation Report:** Included in repository as `EVALUATION-REPORT.md`
9. **Private GitHub Repository:** `sewasetu-assistant` with full git history (`harshnisar` invited).
