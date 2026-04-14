# MVP Remote Deployment Plan (Oref MCP)

This is the practical checklist for the private MVP.

## Goal

Claude.ai can call one remote MCP connector URL from anywhere and get correct Tel Aviv/city alert counts, without running Python on Simon's laptop.

## Current architecture (MVP)

- Israeli compute (recommended GCP `me-west1-a`) runs `oref-mcp/server.py`
- MCP server runs in `streamable-http` mode
- Cloudflare Tunnel exposes HTTPS URL to Claude (`.../mcp`)
- Claude.ai custom connector points to that URL

## Three things to watch

1. Secret URL risk (authless MVP)

- Anyone with the connector URL may try to call the tools.
- For MVP: keep URL private, do not share publicly, avoid screenshots that include full URL.
- Before broader use: add auth (OAuth or token gate).

2. Tunnel URL stability

- Temporary quick tunnel URLs can change after restart.
- For MVP: acceptable.
- If URL changes, update the connector in Claude.
- Later: move to named tunnel + stable hostname.

3. GCP billing surprises

- Free-tier/credits may still require billing enabled.
- Set billing alerts early (small thresholds) and keep VM size minimal (`e2-micro`).
- Stop/delete VM when not needed.

## Out-of-scope for this MVP (intentional)

- Production auth hardening, rate limiting, audit logs
- Uptime SLAs, full monitoring/alerting, backups
- CI/CD, Terraform, Kubernetes, multi-env setups

## Definition of done

- One working connector URL in Claude
- Successful test queries for a fixed date range
- Consistent outputs for Tel Aviv and a second city
