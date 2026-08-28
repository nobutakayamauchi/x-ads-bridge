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


# Current X Ads Analytics metric groups documented for campaign/line-item reporting.
METRIC_GROUPS = (
    "ENGAGEMENT",
    "BILLING",
    "VIDEO",
    "WEB_CONVERSION",
    "MOBILE_CONVERSION",
    "LIFE_TIME_VALUE_MOBILE_CONVERSION",
)
WEBSITE_CLICKS_REQUIRED_GROUPS = ("ENGAGEMENT", "BILLING", "WEB_CONVERSION")
ALLOWED_ENTITIES = {
    "CAMPAIGN",
    "LINE_ITEM",
    "PROMOTED_TWEET",
    "FUNDING_INSTRUMENT",
    "ACCOUNT",
}
ALLOWED_PLACEMENTS = {"ALL_ON_TWITTER", "SPOTLIGHT", "TREND"}
BETA_OBJECTIVE = "WEBSITE_CLICKS"
WEB_CONVERSION_KEYS = (
    "conversion_custom",
    "conversion_site_visits",
    "conversion_sign_ups",
    "conversion_downloads",
    "conversion_purchases",
)


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
    objective = _query_one(query, "objective", BETA_OBJECTIVE).upper()

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
    if objective != BETA_OBJECTIVE:
        raise ReportingError(
            "sellable beta reporting supports WEBSITE_CLICKS only; add the X-defined "
            "metrics for another objective before displaying that campaign"
        )

    return {
        "entity": entity,
        "entity_ids": entity_ids,
        "start_time": start_time,
        "end_time": end_time,
        "granularity": granularity,
        "placement": placement,
        "objective": objective,
    }


def fetch_all_metric_groups(query: dict[str, list[str]]) -> dict[str, Any]:
    request = _validate_request(query)
    account_id = _required_env("XADS_ACCOUNT_ID")
    groups: dict[str, Any] = {}

    # Self-serve dashboard keeps capability for all current X metric groups.
    for group in METRIC_GROUPS:
        command = {
            "action": "stats",
            "account_id": account_id,
            "entity": request["entity"],
            "entity_ids": request["entity_ids"],
            "start_time": request["start_time"],
            "end_time": request["end_time"],
            "granularity": request["granularity"],
            "placement": request["placement"],
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

    report: dict[str, Any] = {
        "ok": True,
        "account_id": account_id,
        "request": request,
        "metric_groups": groups,
        "service_fee_percent": _service_fee_percent(),
        "billing_disclosure": (
            "X Ads spend and Company Service fee are separate. Recent analytics are "
            "estimates; non-spend metrics generally finalize after 24 hours and spend "
            "is generally final within 3 days, with billing adjustments possible later."
        ),
        "display_rule": (
            "When this campaign is displayed, the X-defined WEBSITE_CLICKS metrics in "
            "defined_metrics must be displayed with it. Third-party click/tracking data "
            "must not replace these X-native metrics."
        ),
    }
    report["defined_metrics"] = website_clicks_defined_metrics(report)
    report["cost_summary"] = summarize_costs(report)
    return report


def _numeric_list_sum(value: Any) -> float:
    if not isinstance(value, list):
        return 0.0
    total = 0.0
    for item in value:
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            total += float(item)
    return total


def _iter_metrics(value: Any):
    if isinstance(value, dict):
        metrics = value.get("metrics")
        if isinstance(metrics, dict):
            yield metrics
        for child in value.values():
            yield from _iter_metrics(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_metrics(child)


def _group_response(report: dict[str, Any], group: str) -> Any:
    group_state = ((report.get("metric_groups") or {}).get(group) or {})
    if not group_state.get("available"):
        return None
    return group_state.get("response")


def _sum_scalar_metric(response: Any, metric_name: str) -> float:
    total = 0.0
    for metrics in _iter_metrics(response):
        total += _numeric_list_sum(metrics.get(metric_name))
    return total


def _sum_conversion_metric(response: Any, metric_name: str) -> float:
    total = 0.0
    for metrics in _iter_metrics(response):
        conversion = metrics.get(metric_name)
        if isinstance(conversion, dict):
            # Verified against a live X Ads API WEB_CONVERSION response: conversion
            # count is returned in the nested `metric` array; sale/order fields are
            # intentionally not counted as conversions.
            total += _numeric_list_sum(conversion.get("metric"))
    return total


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _local_from_micro(value: float) -> float:
    return value / 1_000_000.0


def website_clicks_defined_metrics(report: dict[str, Any]) -> dict[str, Any]:
    missing_required = [
        group
        for group in WEBSITE_CLICKS_REQUIRED_GROUPS
        if not (((report.get("metric_groups") or {}).get(group) or {}).get("available"))
    ]
    if missing_required:
        return {
            "objective": BETA_OBJECTIVE,
            "complete": False,
            "missing_required_metric_groups": missing_required,
            "error": "Do not display campaign Data as a compliant WEBSITE_CLICKS report until required X metric groups are available.",
        }

    engagement = _group_response(report, "ENGAGEMENT")
    billing = _group_response(report, "BILLING")
    web = _group_response(report, "WEB_CONVERSION")

    impressions = _sum_scalar_metric(engagement, "impressions")
    clicks = _sum_scalar_metric(engagement, "clicks")
    link_clicks = _sum_scalar_metric(engagement, "url_clicks")
    billed_micro = _sum_scalar_metric(billing, "billed_charge_local_micro")
    site_visits = _sum_conversion_metric(web, "conversion_site_visits")
    conversion_counts = {
        key: _sum_conversion_metric(web, key) for key in WEB_CONVERSION_KEYS
    }
    total_conversions = sum(conversion_counts.values())

    # X documentation defines derived metrics in micros. User-facing monetary
    # values below are converted to the account's local currency.
    cpm_local = _safe_ratio(_local_from_micro(billed_micro) * 1000.0, impressions)
    click_rate = _safe_ratio(clicks, impressions)
    link_click_rate = _safe_ratio(link_clicks, impressions)
    cplc_local = _safe_ratio(_local_from_micro(billed_micro), clicks)
    cost_per_link_click_local = _safe_ratio(
        _local_from_micro(billed_micro), link_clicks
    )
    conversion_rate = _safe_ratio(total_conversions, impressions)
    site_visit_rate = _safe_ratio(site_visits, impressions)
    cpa_local = _safe_ratio(_local_from_micro(billed_micro), total_conversions)
    site_visit_cpa_local = _safe_ratio(_local_from_micro(billed_micro), site_visits)

    return {
        "objective": BETA_OBJECTIVE,
        "complete": True,
        "x_native": {
            "impressions": impressions,
            "clicks": clicks,
            "link_clicks_url_clicks": link_clicks,
            "x_ads_spend_local": _local_from_micro(billed_micro),
            "site_visits": site_visits,
            "conversion_counts": conversion_counts,
            "total_conversions": total_conversions,
        },
        "derived": {
            "cpm_local": cpm_local,
            "click_rate": click_rate,
            "link_click_rate": link_click_rate,
            "cplc_local": cplc_local,
            "cost_per_link_click_local": cost_per_link_click_local,
            "conversion_rate": conversion_rate,
            "site_visit_rate": site_visit_rate,
            "cpa_local": cpa_local,
            "site_visit_cpa_local": site_visit_cpa_local,
        },
        "formulas": {
            "cpm": "spend_local * 1000 / impressions",
            "click_rate": "clicks / impressions",
            "link_click_rate": "url_clicks / impressions",
            "cplc": "spend_local / clicks",
            "cost_per_link_click": "spend_local / url_clicks",
            "total_conversions": "conversion_custom + conversion_site_visits + conversion_sign_ups + conversion_downloads + conversion_purchases (nested metric counts)",
            "conversion_rate": "total_conversions / impressions",
            "site_visit_rate": "conversion_site_visits / impressions",
            "cpa": "spend_local / total_conversions",
            "site_visit_cpa": "spend_local / conversion_site_visits",
        },
    }


def _extract_billed_micro(value: Any) -> int:
    return int(_sum_scalar_metric(value, "billed_charge_local_micro"))


def summarize_costs(report: dict[str, Any]) -> dict[str, float]:
    billing = _group_response(report, "BILLING")
    billed_micro = _extract_billed_micro(billing) if billing is not None else 0
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
<p class="warn">X Ads spend and Company Service fee are separate. Recent analytics are estimates; non-spend metrics generally finalize after 24 hours and spend is generally final within 3 days, with later billing adjustments possible.</p>
<p><strong>Beta reporting objective:</strong> WEBSITE_CLICKS. Every displayed campaign report includes its X-defined objective metrics. Third-party tracking data must be shown only with the corresponding X-native metrics alongside it.</p>
<form id="f">
<label>Campaign objective</label><select name="objective"><option>WEBSITE_CLICKS</option></select>
<label>Entity</label><select name="entity"><option>LINE_ITEM</option><option>CAMPAIGN</option><option>PROMOTED_TWEET</option><option>FUNDING_INSTRUMENT</option><option>ACCOUNT</option></select>
<label>Entity IDs (comma-separated)</label><input name="entity_ids" required>
<label>Start time (ISO 8601, whole-hour boundary)</label><input name="start_time" placeholder="2026-08-28T00:00:00Z" required>
<label>End time (exclusive, ISO 8601)</label><input name="end_time" placeholder="2026-08-29T00:00:00Z" required>
<label>Granularity</label><select name="granularity"><option>TOTAL</option><option>HOUR</option><option>DAY</option></select>
<label>Placement</label><select name="placement"><option>ALL_ON_TWITTER</option><option>SPOTLIGHT</option><option>TREND</option></select>
<button type="submit">Fetch X-native metrics</button>
</form>
<h2>Current X Ads Analytics metric groups</h2><ul>{groups}</ul>
<h2>Result</h2><pre id="out">No query yet.</pre>
<script>
const f=document.getElementById('f'),out=document.getElementById('out');
f.addEventListener('submit',async(e)=>{{e.preventDefault();out.textContent='Loading...';const q=new URLSearchParams(new FormData(f));const r=await fetch('/api/stats?'+q.toString());out.textContent=JSON.stringify(await r.json(),null,2);}});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "AdsDaseRuKunReporting/0.2"

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
