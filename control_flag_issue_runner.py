from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from requests_oauthlib import OAuth1

from control_completion import evaluate_control_completion

BASE_URL = os.getenv("XADS_BASE_URL", "https://ads-api.x.com").rstrip("/")
API_VERSION = os.getenv("XADS_API_VERSION", "12")
DEFAULT_ACCOUNT_ID = os.getenv("XADS_ACCOUNT_ID", "").strip()
RESULT_PATH = Path("result.md")


class ControlFlagError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ControlFlagError(f"missing required secret/env: {name}")
    return value


def _auth() -> OAuth1:
    return OAuth1(
        _required_env("XADS_CONSUMER_KEY"),
        _required_env("XADS_CONSUMER_SECRET"),
        _required_env("XADS_ACCESS_TOKEN"),
        _required_env("XADS_ACCESS_TOKEN_SECRET"),
    )


def _read_command() -> dict[str, Any]:
    event_path = os.getenv("GITHUB_EVENT_PATH", "").strip()
    if not event_path:
        raise ControlFlagError("GITHUB_EVENT_PATH is not configured")
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    body = str(((event.get("issue") or {}).get("body")) or "").strip()
    if not body:
        raise ControlFlagError("issue body must contain JSON")
    command = json.loads(body)
    if not isinstance(command, dict):
        raise ControlFlagError("issue body JSON must be an object")
    return command


def _get(path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(
        f"{BASE_URL}/{API_VERSION}/{path.lstrip('/')}",
        params=params,
        auth=_auth(),
        timeout=45,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text[:4000]}
    if not response.ok:
        raise ControlFlagError(
            f"X Ads API {response.status_code}: {json.dumps(payload, ensure_ascii=False)[:4000]}"
        )
    if not isinstance(payload, dict):
        raise ControlFlagError("X Ads API response must be an object")
    return payload


def _data_object(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return payload


def _floor_hour(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def _parse_time(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ControlFlagError("line item start_time is missing")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ControlFlagError(f"invalid line item time: {text}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_hour(value: datetime) -> str:
    return _floor_hour(value).strftime("%Y-%m-%dT%H:00:00Z")


def _extract_metrics(stats: dict[str, Any]) -> dict[str, int]:
    metrics: dict[str, Any] = {}
    data = stats.get("data")
    if isinstance(data, list) and data:
        id_data = (data[0] or {}).get("id_data") or []
        if isinstance(id_data, list) and id_data:
            metrics = (id_data[0] or {}).get("metrics") or {}

    def first_int(name: str) -> int:
        raw = metrics.get(name)
        if isinstance(raw, list) and raw:
            try:
                return int(raw[0] or 0)
            except (TypeError, ValueError):
                return 0
        try:
            return int(raw or 0)
        except (TypeError, ValueError):
            return 0

    lpv = metrics.get("conversion_landing_page_views") or {}
    lpv_metric = lpv.get("metric") if isinstance(lpv, dict) else None
    lpv_count = 0
    if isinstance(lpv_metric, list) and lpv_metric:
        try:
            lpv_count = int(lpv_metric[0] or 0)
        except (TypeError, ValueError):
            lpv_count = 0

    return {
        "billed_charge_local_micro": first_int("billed_charge_local_micro"),
        "impressions": first_int("impressions"),
        "link_clicks": first_int("link_clicks"),
        "landing_page_views": lpv_count,
    }


def _execute(command: dict[str, Any]) -> dict[str, Any]:
    account_id = str(command.get("account_id") or DEFAULT_ACCOUNT_ID).strip()
    line_item_id = str(command.get("line_item_id") or "").strip()
    if not account_id:
        raise ControlFlagError("account_id is required")
    if not line_item_id:
        raise ControlFlagError("line_item_id is required")

    line_item_payload = _get(f"accounts/{account_id}/line_items/{line_item_id}")
    line_item = _data_object(line_item_payload)

    now = datetime.now(timezone.utc)
    start = _floor_hour(_parse_time(line_item.get("start_time")))
    end = _floor_hour(now)

    # X Stats requires whole-hour boundaries. If the line item is younger than one full
    # hour, return a safe WAIT state instead of querying a future end time.
    if end <= start:
        evaluation = evaluate_control_completion(
            line_item,
            billed_charge_local_micro=0,
            now=now,
            tolerance_jpy=float(command.get("tolerance_jpy", 1.0)),
        )
        return {
            **evaluation,
            "line_item_id": line_item_id,
            "stats_window_ready": False,
            "stats_window": None,
            "metrics": {
                "impressions": 0,
                "link_clicks": 0,
                "landing_page_views": 0,
            },
        }

    stats = _get(
        f"stats/accounts/{account_id}",
        params={
            "entity": "LINE_ITEM",
            "entity_ids": line_item_id,
            "start_time": _iso_hour(start),
            "end_time": _iso_hour(end),
            "granularity": "TOTAL",
            "placement": "ALL_ON_TWITTER",
            "metric_groups": "ENGAGEMENT,BILLING,WEB_CONVERSION",
        },
    )
    observed = _extract_metrics(stats)
    evaluation = evaluate_control_completion(
        line_item,
        billed_charge_local_micro=observed["billed_charge_local_micro"],
        now=now,
        tolerance_jpy=float(command.get("tolerance_jpy", 1.0)),
    )
    return {
        **evaluation,
        "line_item_id": line_item_id,
        "stats_window_ready": True,
        "stats_window": {"start_time": _iso_hour(start), "end_time": _iso_hour(end)},
        "metrics": {
            "impressions": observed["impressions"],
            "link_clicks": observed["link_clicks"],
            "landing_page_views": observed["landing_page_views"],
        },
    }


def _write_result(payload: dict[str, Any]) -> None:
    summary = (
        "## X Control Flag\n\n"
        f"`FLAG={payload.get('FLAG')}`  "
        f"`BUDGET_EXHAUSTED={str(payload.get('BUDGET_EXHAUSTED')).lower()}`  "
        f"`CONTROL_CLOSED={str(payload.get('CONTROL_CLOSED')).lower()}`  "
        f"`READY_FOR_NEXT={str(payload.get('READY_FOR_NEXT')).lower()}`\n\n"
        f"Spend: **¥{payload.get('billed_jpy')} / ¥{payload.get('total_budget_jpy')}**  "
        f"Remaining: **¥{payload.get('remaining_jpy')}**\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n"
    )
    RESULT_PATH.write_text(summary, encoding="utf-8")


def main() -> int:
    try:
        payload = _execute(_read_command())
        _write_result(payload)
        return 0
    except Exception as exc:
        _write_result({"FLAG": "ERROR", "ok": False, "error": str(exc), "read_only": True})
        return 1


if __name__ == "__main__":
    sys.exit(main())
