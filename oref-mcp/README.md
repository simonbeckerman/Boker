# Pikud HaOref Alert History MCP Server

Model Context Protocol (MCP) server that queries the Israeli Home Front Command (Pikud HaOref) historical alerts API and exposes tools for day-by-day rocket/missile alert counts by city (Hebrew area names in the official feed).

**Geo-blocking:** The `oref.org.il` API often returns **Access Denied** for non-Israeli IPs. Run this server on a host with an Israeli IP (see GCP below) or set **`OREF_PROXY_URL`** to an HTTP/HTTPS proxy that exits in Israel.

## Current deployed MVP

- Stable endpoint: `https://boker.z1m3n.com/mcp`
- Runtime: Google Cloud VM in `me-west1-a`
- Auto-start services: `cloudflared` and `boker-mcp`

## Tools

- **`get_alert_data`** — recommended general tool for Claude. Inputs: `city` (optional), `from_date` and `to_date` (optional, YYYY-MM-DD). If `city` is empty it returns nationwide totals. If both dates are empty it defaults to the last 7 days.
- **`get_alerts_nationwide`** — explicit nationwide tool. Inputs: `from_date` and `to_date` are optional (YYYY-MM-DD). If both are missing it defaults to the last 7 days.
- **`get_tel_aviv_alert_count`** — `from_date`, `to_date` (YYYY-MM-DD). Counts category `1` alerts whose `data` field **contains** `תל אביב`.
- **`get_alerts_by_city`** — same plus **`city`**. Hebrew works directly (e.g. `תל אביב`, `חיפה`). Common English names like `Tel Aviv`, `Haifa`, `Jerusalem` are mapped automatically. You can also pass `Israel`, `all cities`, or `nationwide` for a country-wide total.

Both return JSON:

```json
{
  "from_date": "2026-04-08",
  "to_date": "2026-04-14",
  "city_filter": "תל אביב",
  "daily_counts": [
    {"date": "2026-04-08", "count": 3},
    {"date": "2026-04-09", "count": 1}
  ],
  "total": 4
}
```

Every day in the requested range appears in `daily_counts` (zeros included).

## Environment

| Variable | Meaning |
|----------|---------|
| `OREF_PROXY_URL` | Optional. HTTP(S) proxy URL for requests to Oref (e.g. `http://user:pass@host:port`). |
| `OREF_HISTORY_URL` | Optional. Override full history URL (must include `GetAlarmsHistory.aspx` path); otherwise the server tries `www` then `alerts-history`. |
| `MCP_TRANSPORT` | `stdio` (default) for local “spawn process” connectors, or **`streamable-http`** for remote URL connectors (Claude.ai). |
| `MCP_HOST` | Bind address for Streamable HTTP (default: `0.0.0.0` when `MCP_TRANSPORT=streamable-http`, else `127.0.0.1`). |
| `MCP_PORT` | Port for Streamable HTTP (default: `8000`). MCP endpoint path is `/mcp` unless you change FastMCP settings. |

## 1. Local setup

```bash
pip install -r requirements.txt
python server.py
```

Use **Python 3.11+**. By default the process speaks MCP over **stdio** (no HTTP port).

## Remote MCP for Claude.ai (fully hosted)

Claude’s **remote** custom connectors do **not** run `python` on your laptop. Claude’s servers open **HTTPS** to **your** MCP URL. That matches **`streamable-http`** mode.

**Important — two different networks:**

1. **Inbound to your MCP server:** Must be **public HTTPS** (or HTTP for testing only). Claude connects **from Anthropic’s IPs**, not from your PC. If you use a firewall, allow those IPs: [Anthropic IP addresses](https://docs.anthropic.com/en/api/ip-addresses).
2. **Outbound to Oref:** Must still look **Israeli** to `oref.org.il`. Run the **same** Python process on a **VM in Israel** (e.g. GCP `me-west1-a`) **or** set `OREF_PROXY_URL` to a proxy that exits in Israel.

**Browserbase** is a hosted **browser** for sites that need a real browser. This project calls a **simple JSON HTTP API** with headers, so Browserbase is **not** required. If Oref ever required a full browser session from Israel, you could explore that — it’s extra cost and complexity for little benefit here.

**Cloudflare** is useful as **HTTPS + tunnel** (`cloudflared`) so you don’t expose raw ports: your Israeli VM runs `python server.py` on `localhost:8000`, the tunnel presents `https://oref-mcp.example.com` → `http://127.0.0.1:8000`. See [Cloudflare remote MCP guide](https://developers.cloudflare.com/agents/guides/remote-mcp-server/). You can also put **Caddy/nginx** on the VM with a TLS certificate instead of Cloudflare.

**Run in remote mode** (on the Israeli host or behind your proxy):

```bash
export MCP_TRANSPORT=streamable-http
# optional: export MCP_HOST=0.0.0.0 MCP_PORT=8000
pip install -r requirements.txt
python server.py
```

Then in **Claude → Customize → Connectors → Add custom connector**, add your **remote MCP server URL**, for example:

`https://your-domain.com/mcp`

(use your real hostname and `/mcp` unless you changed `streamable_http_path` in code).

Claude supports **authless** remote servers; for production, consider adding **OAuth** per the [MCP authorization spec](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization) so random people cannot call your tools.

## 2. GCP deployment (to get an Israeli IP)

```bash
# Create free VM in Tel Aviv region
gcloud compute instances create oref-mcp \
  --zone=me-west1-a \
  --machine-type=e2-micro \
  --image-family=debian-12 \
  --image-project=debian-cloud

# SSH in, clone repo, install deps, run server
```

Then install Python 3.11+, clone this repo, `pip install -r requirements.txt`, and either:

- **Local stdio:** run `python server.py` where your client spawns the process, **or**
- **Remote URL:** set `MCP_TRANSPORT=streamable-http`, put HTTPS in front (Cloudflare Tunnel / reverse proxy), and add the public `/mcp` URL in Claude (see above).

## 3. Claude.ai custom MCP connector config

### A) Local machine (stdio — process on your computer)

Paste into **Claude.ai → Settings → Connectors → Add custom MCP** (adjust the path to `server.py` on your machine):

```json
{
  "mcpServers": {
    "oref-alerts": {
      "command": "python",
      "args": ["/path/to/oref-mcp/server.py"]
    }
  }
}
```

If `python` is not Python 3.11+, use the full path to the interpreter, e.g. `"/usr/bin/python3.11"`.

### B) Remote server (Streamable HTTP — URL in Claude)

Use **Customize → Connectors → Add custom connector** and enter your HTTPS MCP endpoint, e.g. `https://your-domain.com/mcp` (no JSON file — the UI asks for the **URL**).

## 4. Test queries to run in Claude once connected

- "How many sirens sounded in Tel Aviv on April 8 2026?"
- "Give me a daily siren count for Tel Aviv from April 8 to April 14 2026"
- "Which day had the most alerts in Tel Aviv since April 1 2026?"
- "Give me a daily siren count for Haifa from April 8 to April 14 2026 (use the city tool)."
- "Give me a nationwide daily siren count for the last week."
- "Use get_alerts_nationwide for today."

## Data source

- Endpoint (tries `www.oref.org.il` first, then `alerts-history.oref.org.il`): `.../Shared/Ajax/GetAlarmsHistory.aspx?lang=he&fromDate=YYYY-MM-DD&toDate=YYYY-MM-DD&mode=0`
- Required headers: `Referer: https://www.oref.org.il/`, `X-Requested-With: XMLHttpRequest`

Only alerts with **`category` 1** (rocket/missile) are counted; city/area matching uses **substring** match on the **`data`** field.
