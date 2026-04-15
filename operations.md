# operations

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

## Endpoint quick test

```bash
curl -sS -X POST "https://boker.z1m3n.com/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"ops-check","version":"1.0"}}}'
```

Expected: JSON result with `serverInfo.name = "oref-alerts"`.

## Known normal behaviors

- Browser GET to `/mcp` may show a `Not Acceptable` style JSON error.
- This does not mean the server is down; MCP expects POST with specific headers.

## Incident triage order

1. Check Anthropic/Claude outage status
2. Check Cloudflare tunnel health
3. Check VM service status (`boker-mcp`, `cloudflared`)
4. Check Oref upstream response behavior
