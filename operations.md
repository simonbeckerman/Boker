# operations

## Local operator machine

- `gcloud` CLI is installed on this Mac via Homebrew cask `gcloud-cli`.
- Installed binary path: `/opt/homebrew/Caskroom/gcloud-cli/565.0.0/google-cloud-sdk/bin/gcloud`
- Quick check:

```bash
/opt/homebrew/Caskroom/gcloud-cli/565.0.0/google-cloud-sdk/bin/gcloud --version
```

## What is running

- Cloudflare tunnel service: `cloudflared`
- Boker MCP service: `boker-mcp`
- Public endpoint: `https://boker.z1m3n.com/mcp`

## Daily health check (fast)

1. Cloudflare tunnel is healthy (via Cloudflare MCP/API)
2. MCP initialize works on public endpoint
3. Tool call returns valid JSON

## VM service checks

Run on VM:

```bash
systemctl is-active cloudflared
systemctl is-active boker-mcp
```

Both should return `active`.

## Restart services (if needed)

Run on VM:

```bash
sudo systemctl restart boker-mcp
sudo systemctl restart cloudflared
```

## Deploy update flow (GitHub -> VM)

When code changes are pushed to `main`, deploy with:

```bash
sudo -u simon_beckerman -H bash -lc 'cd /home/simon_beckerman/Boker && git pull --ff-only origin main'
sudo systemctl restart boker-mcp
sudo systemctl status boker-mcp --no-pager -l
```

Expected:

- `git pull` shows a fast-forward (or already up to date)
- `boker-mcp` returns `active (running)`

## Endpoint quick test

```bash
curl -sS -X POST "https://boker.z1m3n.com/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"ops-check","version":"1.0"}}}'
```

Expected: JSON result with `serverInfo.name = "oref-alerts"`.

## Multi-city smoke test

```bash
curl -sS -X POST "https://boker.z1m3n.com/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  --data '{"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"get_alert_data","arguments":{"city":"Haifa","from_date":"2026-04-08","to_date":"2026-04-14"}}}'
```

Expected:

- Response is successful (`"isError": false`)
- `structuredContent.scope` is `"city"`
- `structuredContent.normalized_city` is Hebrew (for this example: `"חיפה"`)

## Nationwide smoke test (new default flow)

```bash
curl -sS -X POST "https://boker.z1m3n.com/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  --data '{"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"get_alert_data","arguments":{"city":"Israel","from_date":"2026-04-08","to_date":"2026-04-14"}}}'
```

Expected:

- Response is successful (`"isError": false`)
- `structuredContent.scope` is `"nationwide"`
- `structuredContent.city_filter` is `null`

## Known normal behaviors

- Browser GET to `/mcp` may show a `Not Acceptable` style JSON error.
- This does not mean the server is down; MCP expects POST with specific headers.

## Incident triage order

1. Check Anthropic/Claude outage status
2. Check Cloudflare tunnel health
3. Check VM service status (`boker-mcp`, `cloudflared`)
4. Check Oref upstream response behavior
