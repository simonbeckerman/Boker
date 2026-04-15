# plan

## Goal

Keep a private MVP running end-to-end:
- Claude can call one stable connector URL
- data is fetched from Oref history via Israeli egress
- no laptop dependency for runtime

## Current state (completed)

- Runtime host: Google Cloud VM `oref-mcp` in `me-west1-a`
- App: `oref-mcp/server.py` in `streamable-http` mode
- Public MCP URL: `https://boker.z1m3n.com/mcp`
- Cloudflare tunnel: named tunnel `boker-mcp` (healthy)
- Auto-start services on VM:
  - `cloudflared` service
  - `boker-mcp` systemd service
- Claude connector: points to `https://boker.z1m3n.com/mcp`

## MVP boundaries

In scope:
- Reliable private demo path
- Simple operations and manual recovery steps
- Documentation in repo

Out of scope (for now):
- OAuth-protected MCP endpoint
- formal CI/CD and infra-as-code
- multi-env production standards

## Risks to monitor

1. Upstream API drift (Oref endpoint behavior changes)
2. Platform outage (Claude/Anthropic incidents)
3. Cost drift (GCP if VM left running permanently)

## Next priorities

1. Add endpoint auth before sharing broadly
2. Add lightweight uptime monitor + alert
3. Rotate sensitive local tokens and remove hardcoded secrets from user-level configs
