"""
MCP server: Pikud HaOref (Israeli Home Front Command) historical alerts.

Requires network access from an Israeli IP or OREF_PROXY_URL — see README.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from typing import Any, Awaitable, Callable
from zoneinfo import ZoneInfo

import anyio
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# ASGI types (minimal typing for the wrapper)
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]
Scope = dict[str, Any]

# History AJAX: `www` sometimes 404s; official history UI often lives on `alerts-history`.
OREF_HISTORY_ENDPOINTS: list[tuple[str, dict[str, str]]] = [
    (
        "https://www.oref.org.il/Shared/Ajax/GetAlarmsHistory.aspx",
        {
            "Referer": "https://www.oref.org.il/",
            "X-Requested-With": "XMLHttpRequest",
        },
    ),
    (
        "https://alerts-history.oref.org.il/Shared/Ajax/GetAlarmsHistory.aspx",
        {
            "Referer": "https://alerts-history.oref.org.il/",
            "X-Requested-With": "XMLHttpRequest",
        },
    ),
]
TEL_AVIV_SUBSTRING = "תל אביב"
ALL_CITIES_SENTINEL = "__ALL_CITIES__"
IL_TZ = ZoneInfo("Asia/Jerusalem")
CITY_ALIASES: dict[str, str] = {
    "tel aviv": "תל אביב",
    "tel-aviv": "תל אביב",
    "tel aviv-yafo": "תל אביב",
    "tel aviv yafo": "תל אביב",
    "jerusalem": "ירושלים",
    "haifa": "חיפה",
    "beer sheva": "באר שבע",
    "be'er sheva": "באר שבע",
    "beersheba": "באר שבע",
    "ashkelon": "אשקלון",
    "ashdod": "אשדוד",
    "netanya": "נתניה",
    "rishon lezion": "ראשון לציון",
    "petah tikva": "פתח תקווה",
    "petach tikva": "פתח תקווה",
    "holon": "חולון",
    "bat yam": "בת ים",
    "herzliya": "הרצליה",
    "kfar saba": "כפר סבא",
    "rehovot": "רחובות",
    "israel": ALL_CITIES_SENTINEL,
    "all israel": ALL_CITIES_SENTINEL,
    "all of israel": ALL_CITIES_SENTINEL,
    "rest of israel": ALL_CITIES_SENTINEL,
    "nationwide": ALL_CITIES_SENTINEL,
    "all": ALL_CITIES_SENTINEL,
    "all cities": ALL_CITIES_SENTINEL,
    "ישראל": ALL_CITIES_SENTINEL,
    "כל הארץ": ALL_CITIES_SENTINEL,
}


def _transport() -> str:
    return os.environ.get("MCP_TRANSPORT", "stdio").strip().lower()


def _default_bind_host() -> str:
    # Remote / Claude.ai connectors need Streamable HTTP on all interfaces unless proxied.
    return "0.0.0.0" if _transport() == "streamable-http" else "127.0.0.1"


def _transport_security() -> TransportSecuritySettings | None:
    """
    Behind Cloudflare Tunnel, requests use Host: *.trycloudflare.com, not 127.0.0.1.
    DNS rebinding protection would return 421 Misdirected Request unless disabled for this mode.
    """
    if _transport() == "streamable-http":
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return None


# stateless + JSON responses: recommended for Streamable HTTP (Claude remote MCP).
mcp = FastMCP(
    "oref-alerts",
    stateless_http=True,
    json_response=True,
    host=os.environ.get("MCP_HOST", _default_bind_host()),
    port=int(os.environ.get("MCP_PORT", "8000")),
    transport_security=_transport_security(),
)


def _parse_ymd(s: str) -> date:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def _today_il() -> date:
    return datetime.now(IL_TZ).date()


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
    if city == ALL_CITIES_SENTINEL:
        return True
    return city in (data or "")


def _normalize_city_filter(city: str) -> str:
    """
    Accept Hebrew directly and map common English names to Hebrew substrings.
    """
    city_clean = (city or "").strip()
    if not city_clean:
        return ""
    return CITY_ALIASES.get(city_clean.lower(), city_clean)


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
    override = (os.environ.get("OREF_HISTORY_URL") or "").strip()
    endpoints: list[tuple[str, dict[str, str]]] = (
        [(override, OREF_HISTORY_ENDPOINTS[0][1])] if override else OREF_HISTORY_ENDPOINTS
    )

    last_status: int | None = None
    last_snippet = ""

    async with httpx.AsyncClient(
        proxy=proxy,
        timeout=httpx.Timeout(60.0),
        follow_redirects=True,
    ) as client:
        for url, headers in endpoints:
            r = await client.get(url, params=params, headers=headers)
            last_status = r.status_code
            last_snippet = (r.text or "")[:120].replace("\n", " ")
            if r.status_code == 404:
                continue
            r.raise_for_status()
            text = r.text.strip()
            if not text:
                continue
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

    if last_status == 404:
        return []
    raise RuntimeError(
        f"Oref history request failed (last HTTP {last_status}): {last_snippet!r}"
    )


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


def _resolve_date_range(from_date: str, to_date: str) -> tuple[date, date]:
    """
    Resolve date range with MVP-friendly defaults:
    - both missing -> last 7 days (today and 6 days back, IL timezone)
    - one missing -> use the provided day for both endpoints
    """
    from_raw = (from_date or "").strip()
    to_raw = (to_date or "").strip()

    if not from_raw and not to_raw:
        end = _today_il()
        start = end - timedelta(days=6)
        return start, end

    if from_raw and not to_raw:
        d = _parse_ymd(from_raw)
        return d, d

    if to_raw and not from_raw:
        d = _parse_ymd(to_raw)
        return d, d

    start = _parse_ymd(from_raw)
    end = _parse_ymd(to_raw)
    if start > end:
        raise ValueError("from_date must be on or before to_date")
    return start, end


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
    field (e.g. "תל אביב", "חיפה"). Common English city names (e.g. "Tel Aviv",
    "Haifa", "Jerusalem") are also accepted and mapped automatically. You can also
    pass "Israel", "all cities", or "nationwide" to get a country-wide count.
    Only rocket/missile alerts (category 1) are counted.
    """
    city_filter = _normalize_city_filter(city)
    if not city_filter:
        raise ValueError("city must be a non-empty Hebrew substring")
    return await _alerts_report(from_date, to_date, city_filter)


@mcp.tool()
async def get_alert_data(
    city: str = "",
    from_date: str = "",
    to_date: str = "",
) -> dict[str, Any]:
    """
    General alert data tool for natural-language requests.

    - If `city` is empty: returns nationwide totals (all cities/areas).
    - If `city` is provided: matches that city/area (Hebrew substring), with
      English aliases mapped automatically.
    - If both dates are empty: defaults to last 7 days in Israel timezone.
    - If only one date is provided: uses that same date as a single-day query.

    Dates must be YYYY-MM-DD when provided. Counts only category 1 alerts.
    """
    start_d, end_d = _resolve_date_range(from_date, to_date)
    from_s = start_d.isoformat()
    to_s = end_d.isoformat()

    requested_city = (city or "").strip()
    city_filter = _normalize_city_filter(requested_city)
    scope = "city"
    if not city_filter:
        city_filter = ALL_CITIES_SENTINEL
        scope = "nationwide"
    elif city_filter == ALL_CITIES_SENTINEL:
        scope = "nationwide"

    report = await _alerts_report(from_s, to_s, city_filter)
    if city_filter == ALL_CITIES_SENTINEL:
        report["city_filter"] = None

    report["scope"] = scope
    report["requested_city"] = requested_city or None
    report["normalized_city"] = None if city_filter == ALL_CITIES_SENTINEL else city_filter
    report["timezone"] = "Asia/Jerusalem"
    report["source"] = "oref-history"
    report["is_partial"] = False
    return report


@mcp.tool()
async def get_alerts_nationwide(
    from_date: str = "",
    to_date: str = "",
) -> dict[str, Any]:
    """
    Explicit nationwide alert tool.

    Returns country-wide day-by-day counts (all cities/areas) for category 1 alerts.
    Dates are optional:
    - both missing -> last 7 days in Israel timezone
    - only one provided -> single-day query
    - both provided -> inclusive range (YYYY-MM-DD)
    """
    start_d, end_d = _resolve_date_range(from_date, to_date)
    report = await _alerts_report(start_d.isoformat(), end_d.isoformat(), ALL_CITIES_SENTINEL)
    report["city_filter"] = None
    report["scope"] = "nationwide"
    report["requested_city"] = None
    report["normalized_city"] = None
    report["timezone"] = "Asia/Jerusalem"
    report["source"] = "oref-history"
    report["is_partial"] = False
    return report


class _AcceptClaudeWildcardASGI:
    """
    Claude.ai sends Accept: */* on MCP requests. Older mcp Python builds reject that
    with 406 before the handshake runs; Claude then shows 'Couldn't reach the MCP server'.
    Normalize */* (and empty Accept) to application/json for Streamable HTTP JSON mode.
    """

    def __init__(self, app: Any) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") == "http":
            raw_headers = scope.get("headers") or []
            accept_val = ""
            for key, val in raw_headers:
                if key.lower() == b"accept":
                    accept_val = val.decode("latin-1")
                    break
            low = accept_val.lower()
            if "application/json" not in low and (
                not accept_val.strip() or "*/*" in low or low.strip() == "*/*"
            ):
                new_headers = [(k, v) for k, v in raw_headers if k.lower() != b"accept"]
                new_headers.append((b"accept", b"application/json"))
                scope = {**scope, "headers": new_headers}
        await self._app(scope, receive, send)


async def _run_streamable_http_async() -> None:
    import uvicorn

    inner = mcp.streamable_http_app()
    app: Any = _AcceptClaudeWildcardASGI(inner)
    config = uvicorn.Config(
        app,
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=mcp.settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    transport = _transport()
    if transport == "streamable-http":
        anyio.run(_run_streamable_http_async)
    elif transport in ("stdio", ""):
        mcp.run(transport="stdio")
    else:
        raise ValueError(
            f"Unknown MCP_TRANSPORT={transport!r}. Use 'stdio' (default) or 'streamable-http'."
        )


if __name__ == "__main__":
    main()
