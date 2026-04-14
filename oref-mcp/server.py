"""
MCP server: Pikud HaOref (Israeli Home Front Command) historical alerts.

Requires network access from an Israeli IP or OREF_PROXY_URL — see README.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from mcp.server.fastmcp import FastMCP

OREF_BASE = "https://www.oref.org.il/Shared/Ajax/GetAlarmsHistory.aspx"
OREF_HEADERS = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
}
TEL_AVIV_SUBSTRING = "תל אביב"
IL_TZ = ZoneInfo("Asia/Jerusalem")


def _transport() -> str:
    return os.environ.get("MCP_TRANSPORT", "stdio").strip().lower()


def _default_bind_host() -> str:
    # Remote / Claude.ai connectors need Streamable HTTP on all interfaces unless proxied.
    return "0.0.0.0" if _transport() == "streamable-http" else "127.0.0.1"


# stateless + JSON responses: recommended for Streamable HTTP (Claude remote MCP).
mcp = FastMCP(
    "oref-alerts",
    stateless_http=True,
    json_response=True,
    host=os.environ.get("MCP_HOST", _default_bind_host()),
    port=int(os.environ.get("MCP_PORT", "8000")),
)


def _parse_ymd(s: str) -> date:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def _iter_dates_inclusive(start: date, end: date) -> list[date]:
    out: list[date] = []
    d = start
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def _is_rocket_category(raw: Any) -> bool:
    if raw is None:
        return False
    try:
        return int(raw) == 1
    except (TypeError, ValueError):
        return False


def _city_matches(data: str, city: str) -> bool:
    if not city:
        return False
    return city in (data or "")


def _parse_alert_local_date(alert_date: str) -> date:
    """
    Calendar date in Asia/Jerusalem for bucketing.
    Supports ISO-like timestamps and DD/MM/YYYY as returned by some feeds.
    """
    s = (alert_date or "").strip()
    if not s:
        raise ValueError("empty alertDate")

    if len(s) >= 10 and s[2] == "/" and s[5] == "/":
        dd, mm, yy = s[:10].split("/")
        return date(int(yy), int(mm), int(dd))

    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        iso = s.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(iso)
        except ValueError:
            dt = datetime.fromisoformat(s[:10])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IL_TZ)
        return dt.astimezone(IL_TZ).date()

    raise ValueError(f"unrecognized alertDate: {s!r}")


async def _fetch_alarms(from_date: str, to_date: str) -> list[dict[str, Any]]:
    params = {
        "lang": "he",
        "fromDate": from_date,
        "toDate": to_date,
        "mode": "0",
    }
    proxy = os.environ.get("OREF_PROXY_URL") or None
    async with httpx.AsyncClient(
        proxy=proxy,
        timeout=httpx.Timeout(60.0),
        headers=OREF_HEADERS,
        follow_redirects=True,
    ) as client:
        r = await client.get(OREF_BASE, params=params)
        r.raise_for_status()
        text = r.text.strip()
        if not text:
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                "Oref did not return JSON (often Access Denied / geo-block or an HTML error page). "
                "Run from an Israeli IP or set OREF_PROXY_URL."
            ) from e
        if not isinstance(data, list):
            raise RuntimeError(
                "Unexpected Oref response: expected a JSON array. "
                "If you see Access Denied, check IP/geo or OREF_PROXY_URL."
            )
        return [x for x in data if isinstance(x, dict)]


def _build_daily_report(
    from_d: date,
    to_d: date,
    city_filter: str,
    alerts: list[dict[str, Any]],
) -> dict[str, Any]:
    days = _iter_dates_inclusive(from_d, to_d)
    counts: dict[date, int] = {d: 0 for d in days}

    for a in alerts:
        if not _is_rocket_category(a.get("category")):
            continue
        data = str(a.get("data") or "")
        if not _city_matches(data, city_filter):
            continue
        try:
            ad = _parse_alert_local_date(str(a.get("alertDate") or ""))
        except ValueError:
            continue
        if ad in counts:
            counts[ad] += 1

    daily_counts = [{"date": d.isoformat(), "count": counts[d]} for d in days]
    total = sum(counts.values())
    return {
        "from_date": from_d.isoformat(),
        "to_date": to_d.isoformat(),
        "city_filter": city_filter,
        "daily_counts": daily_counts,
        "total": total,
    }


async def _alerts_report(from_date: str, to_date: str, city: str) -> dict[str, Any]:
    from_d = _parse_ymd(from_date)
    to_d = _parse_ymd(to_date)
    if from_d > to_d:
        raise ValueError("from_date must be on or before to_date")

    alerts = await _fetch_alarms(from_date, to_date)
    return _build_daily_report(from_d, to_d, city, alerts)


@mcp.tool()
async def get_tel_aviv_alert_count(from_date: str, to_date: str) -> dict[str, Any]:
    """
    Day-by-day count of rocket/missile alert activations (category 1) where the area
    name contains "תל אביב", for each day between from_date and to_date (inclusive).

    Dates must be YYYY-MM-DD. Requires Israeli IP or OREF_PROXY_URL — see README.
    """
    return await _alerts_report(from_date, to_date, TEL_AVIV_SUBSTRING)


@mcp.tool()
async def get_alerts_by_city(
    from_date: str,
    to_date: str,
    city: str,
) -> dict[str, Any]:
    """
    Same as Tel Aviv tool, but `city` is a Hebrew substring to match inside the `data`
    field (e.g. "תל אביב", "חיפה"). Only rocket/missile alerts (category 1) are counted.
    """
    if not (city or "").strip():
        raise ValueError("city must be a non-empty Hebrew substring")
    return await _alerts_report(from_date, to_date, city.strip())


def main() -> None:
    transport = _transport()
    if transport == "streamable-http":
        mcp.run(transport="streamable-http")
    elif transport in ("stdio", ""):
        mcp.run(transport="stdio")
    else:
        raise ValueError(
            f"Unknown MCP_TRANSPORT={transport!r}. Use 'stdio' (default) or 'streamable-http'."
        )


if __name__ == "__main__":
    main()
