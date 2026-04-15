# Boker In Plain English

This file explains how the app works in everyday language.

## What this app is

Boker is a helper service for Claude.

You ask Claude a question like:
- "How many sirens were there in Tel Aviv between these dates?"

Claude asks Boker.
Boker fetches official alert history data, counts what you asked for, and sends the result back.

## The 3-part chain

The system is a simple chain:

1. Claude (the chat you use)
2. Cloudflare URL (`boker.z1m3n.com`)
3. Boker app on a Google Cloud VM in Israel

## Why there is a VM in Israel

The Oref history source can be picky about location.
Running Boker on an Israeli cloud machine helps make sure data requests work reliably.

## What happens when you ask a question

When you ask Claude for alert counts:

1. Claude sends the request to `https://boker.z1m3n.com/mcp`
2. Cloudflare forwards it securely to your VM
3. Boker reads your date range and city filter
4. Boker requests data from Oref history
5. Boker filters and counts matching alerts per day
6. Boker returns clean JSON to Claude
7. Claude shows you the answer

## What each piece does

- Claude: the front door
- Cloudflare: secure forwarding + stable public URL
- Google Cloud VM: always-on computer
- Boker (`server.py`): the logic that fetches and counts alert history

## Why this setup is good

- Works from anywhere (stable URL)
- Does not require your laptop to stay on
- Keeps one simple connector in Claude

## What can fail (and what it looks like)

- Claude outage: chat side errors even if your setup is healthy
- Cloudflare tunnel down: Claude cannot reach your server
- Boker process down: URL exists but tool calls fail
- Oref API changes: counts may be empty or errors can appear

## Current status (target state)

- Stable MCP URL: `https://boker.z1m3n.com/mcp`
- Cloudflare tunnel service: running
- Boker server: running
- Claude connector: connected

If all four are healthy, the system works end-to-end.

