from __future__ import annotations

import base64
import html
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import bridge


METRIC_GROUPS = (
    "ENGAGEMENT",
    "BILLING",
    "VIDEO",
    "MEDIA",
    "WEB_CONVERSION",
    "MOBILE_CONVERSION",
    "LIFE_TIME_VALUE_MOBILE_CONVERSION",
)
ALLOWED_ENTITIES = {
    "CAMPAIGN",
    "LINE_ITEM",
    "PROMOTED_TWEET",
    "MEDIA_CREATIVE",
    "FUNDING_INSTRUMENT",
    "ACCOUNT",
}
ALLOWED_PLACEMENTS = {"ALL_ON_TWITTER", "SPOTLIGHT", "TREND", "PUBLISHER_NETWORK"}


class ReportingError(ValueError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ReportingError(f"missing required env: {name}")
    return value


def _service_fee_percent() -> float:
    raw = os.getenv("XADS_SERVICE_FEE_PERCENT", "10").strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ReportingError("XADS_SERVICE_FEE_PERCENT must be numeric") from exc
    if value < 0:
        raise ReportingError("XADS_SERVICE_FEE_PERCENT must be >= 0")
    return value


def _query_one(query: dict[str, list[str]], key: str, default: str = "") -> str:
    values = query.get(key) or []
    return str(values[0] if values else default).strip()


def _validate_request(query: dict[str, list[str]]) -> dict[str, str]:
    entity = _query_one(query, "entity", "LINE_ITEM").upper()
    entity_ids = _query_one(query, "entity_ids")
    start_time = _query_one(query, "start_time")
    end_time = _query_one(query, "end_time")
    granularity = _query_one(query, "granularity", "TOTAL").upper()
    placement = _query_one(query, "placement", "ALL_ON_TWITTER").upper()

    if entity not in ALLOWED_ENTITIES:
        raise ReportingError("unsupported entity")
    if not entity_ids:
        raise ReportingError("entity_ids is required")
    if not start_time or not end_time:
        raise ReportingError("start_time and end_time are required")
    if granularity not in {"TOTAL", "DAY", "HOUR"}:
        raise ReportingError("granularity must be TOTAL, DAY, or HOUR")
    if placement not in ALLOWED_PLACEMENTS:
        raise ReportingError("unsupported placement")

    return {
        "entity": entity,
        "entity_ids": entity_ids,
        "start_time": start_time,
        "end_time": end_time,
        "granularity": granularity,
        "placement": placement,
    }


def fetch_all_metric_groups(query: dict[str, list[str]]) -> dict[str, Any]:
    request = _validate_request(query)
    account_id = _required_env("XADS_ACCOUNT_ID")
    groups: dict[str, Any] = {}

    for group in METRIC_GROUPS:
        command = {
            "action": "stats",
            "account_id": account_id,
            **request,
            "metric_groups": group,
        }
        try:
            groups[group] = {
                "available": True,
                "response": bridge.execute(command),
            }
        except Exception as exc:
            groups[group] = {
                "available": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    return {
        "ok": True,
        "account_id": account_id,
        "request": request,
        "metric_groups": groups,
        "service_fee_percent": _service_fee_percent(),
        "billing_disclosure": (
            "X Ads spend and Company Service fee are separate. Recent analytics may be "
            "provisional; billed spend can be adjusted after delivery."
        ),
    }


def _extract_billed_micro(value: Any) -> int:
    total = 0
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "billed_charge_local_micro" and isinstance(child, list):
                for item in child:
                    if isinstance(item, int):
                        total += item
            else:
                total += _extract_billed_micro(child)
    elif isinstance(value, list):
        for child in value:
            total += _extract_billed_micro(child)
    return total


def summarize_costs(report: dict[str, Any]) -> dict[str, float]:
    billing = ((report.get("metric_groups") or {}).get("BILLING") or {})
    billed_micro = 0
    if billing.get("available"):
        billed_micro = _extract_billed_micro(billing.get("response"))
    spend = billed_micro / 1_000_000
    fee = spend * (float(report.get("service_fee_percent") or 0) / 100.0)
    return {
        "x_ads_spend_local": spend,
        "company_service_fee_local": fee,
        "combined_economic_cost_local": spend + fee,
    }


def _expected_basic_header() -> str:
    username = _required_env("XADS_REPORT_USERNAME")
    password = _required_env("XADS_REPORT_PASSWORD")
    encoded = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


def _authorized(header: str | None) -> bool:
    if not header:
        return False
    try:
        expected = _expected_basic_header()
    except ReportingError:
        return False
    import hmac

    return hmac.compare_digest(header, expected)


def _index_html() -> str:
    groups = "".join(f"<li><code>{html.escape(group)}</code></li>" for group in METRIC_GROUPS)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ads DaseRu Kun — X Ads Reporting</title>
<style>body{{font-family:system-ui,sans-serif;max-width:980px;margin:32px auto;padding:0 16px}}input,select,button{{font:inherit;padding:8px;margin:4px 0;width:100%;box-sizing:border-box}}pre{{white-space:pre-wrap;background:#f4f4f4;padding:12px;overflow:auto}}.warn{{padding:12px;background:#fff4d6}}label{{font-weight:600}}</style></head><body>
<h1>Ads DaseRu Kun — X Ads Reporting</h1>
<p class="warn">X Ads spend and Company Service fee are separate. Recent analytics may be provisional and billed spend can be adjusted after delivery.</p>
<form id="f">
<label>Entity</label><select name="entity"><option>LINE_ITEM</option><option>CAMPAIGN</option><option>PROMOTED_TWEET</option><option>MEDIA_CREATIVE</option><option>FUNDING_INSTRUMENT</option><option>ACCOUNT</option></select>
<label>Entity IDs (comma-separated)</label><input name="entity_ids" required>
<label>Start time (ISO 8601, whole-hour boundary)</label><input name="start_time" placeholder="2026-08-28T00:00:00Z" required>
<label>End time (exclusive, ISO 8601)</label><input name="end_time" placeholder="2026-08-29T00:00:00Z" required>
<label>Granularity</label><select name="granularity"><option>TOTAL</option><option>HOUR</option><option>DAY</option></select>
<label>Placement</label><select name="placement"><option>ALL_ON_TWITTER</option><option>SPOTLIGHT</option><option>TREND</option><option>PUBLISHER_NETWORK</option></select>
<button type="submit">Fetch X-native metrics</button>
</form>
<h2>Supported metric groups</h2><ul>{groups}</ul>
<h2>Result</h2><pre id="out">No query yet.</pre>
<script>
const f=document.getElementById('f'),out=document.getElementById('out');
f.addEventListener('submit',async(e)=>{{e.preventDefault();out.textContent='Loading...';const q=new URLSearchParams(new FormData(f));const r=await fetch('/api/stats?'+q.toString());out.textContent=JSON.stringify(await r.json(),null,2);}});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "AdsDaseRuKunReporting/0.1"

    def _auth_or_401(self) -> bool:
        if _authorized(self.headers.get("Authorization")):
            return True
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="Ads DaseRu Kun"')
        self.end_headers()
        return False

    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if not self._auth_or_401():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = _index_html().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/stats":
            try:
                report = fetch_all_metric_groups(parse_qs(parsed.query))
                report["cost_summary"] = summarize_costs(report)
                self._send_json(HTTPStatus.OK, report)
            except ReportingError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            return
        if parsed.path == "/disconnect":
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "disconnect": [
                        "Revoke the connected app at https://x.com/settings/connected_apps",
                        "Set XADS_ALLOW_WRITES=false or disable/delete this dedicated deployment",
                        "Remove X OAuth/access secrets from the dedicated secret store",
                    ],
                },
            )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def log_message(self, format: str, *args: object) -> None:
        # Avoid accidental query-string logging of entity IDs/time ranges in beta.
        return


def main() -> int:
    _required_env("XADS_REPORT_USERNAME")
    _required_env("XADS_REPORT_PASSWORD")
    _required_env("XADS_ACCOUNT_ID")
    host = os.getenv("XADS_REPORT_HOST", "127.0.0.1")
    port = int(os.getenv("XADS_REPORT_PORT", "8787"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"reporting dashboard listening on http://{host}:{port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
