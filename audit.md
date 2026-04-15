# audit

Scope: Boker MVP prototype (not production infrastructure).

Date: 2026-04-15

## 1) Project structure

PASS

- `oref-mcp/server.py` present
- `oref-mcp/requirements.txt` present
- `oref-mcp/README.md` present
- Supporting docs: `howitworks.md`, `plan.md`, `operations.md`

## 2) Environment/tooling for this architecture

PASS (MVP level)

- Python app deploy path validated
- Cloudflare tunnel + domain routing validated
- Google Cloud VM exists and is running in `me-west1-a`

Notes:
- This project does not require `wrangler.toml` because runtime is VM-based, not Workers-based.

## 3) Cloudflare configuration

PASS

- Named tunnel `boker-mcp` configured
- Published route `boker.z1m3n.com` -> `http://127.0.0.1:8000`
- Tunnel status healthy with active connections

## 4) Deployment readiness

PASS (for MVP goals)

- Public MCP endpoint responds: `https://boker.z1m3n.com/mcp`
- Claude connector uses stable domain (no temporary URL dependence)
- Reboot recovery tested and passed

## 5) Secrets and environment hygiene

PARTIAL

Strengths:
- Cloudflare API MCP connected via OAuth flow
- Project-level MCP config excludes Pinecone for this repo (`.cursor/mcp.json`)

Gaps:
- User-global MCP config still contains a plain-text Pinecone API key.

Action:
- Rotate Pinecone key and remove hardcoded key from global config.

## 6) Git state and CI readiness

PARTIAL

Strengths:
- Repo initialized and pushed
- Core docs and code tracked

Gaps:
- Local uncommitted changes may exist before next commit (normal during active session).
- No CI pipeline (intentionally out of MVP scope).

## 7) Operations resilience

PASS

- `cloudflared` system service enabled
- `boker-mcp` system service enabled
- Both verified active after remote reboot test

## Final verdict

MVP goal status: PASS

This project is correctly set up for a private MVP demo from anywhere, using a stable Claude connector URL and auto-recovering services on reboot.
