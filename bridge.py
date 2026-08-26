from __future__ import annotations

import json
import os
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from requests_oauthlib import OAuth1

BASE_URL = os.getenv("XADS_BASE_URL", "https://ads-api.x.com")
API_VERSION = os.getenv("XADS_API_VERSION", "12")
DEFAULT_ACCOUNT_ID = os.getenv("XADS_ACCOUNT_ID", "").strip()
WRITE_COMMANDS = {
    "pause_campaign",
    "resume_campaign",
    "set_daily_budget",
    "pause_line_item",
    "resume_line_item",
}


class BridgeError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise BridgeError(f"missing required secret/env: {name}")
    return value


def _auth() -> OAuth1:
    return OAuth1(
        _required_env("XADS_CONSUMER_KEY"),
        _required_env("XADS_CONSUMER_SECRET"),
        _required_env("XADS_ACCESS_TOKEN"),
        _required_env("XADS_ACCESS_TOKEN_SECRET"),
    )


def _url(path: str) -> str:
    return f"{BASE_URL.rstrip('/')}/{API_VERSION}/{path.lstrip('/')}"


def _request(method: str, path: str, *, params: dict[str, Any] | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.request(
        method,
        _url(path),
        params=params,
        data=data,
        auth=_auth(),
        timeout=45,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text[:4000]}
    if not response.ok:
        raise BridgeError(f"X Ads API {response.status_code}: {json.dumps(payload, ensure_ascii=False)[:4000]}")
    return payload


def _account(command: dict[str, Any]) -> str:
    account_id = str(command.get("account_id") or DEFAULT_ACCOUNT_ID).strip()
    if not account_id:
        raise BridgeError("account_id is required (command.account_id or XADS_ACCOUNT_ID)")
    return account_id


def _write_guard(command_name: str) -> None:
    if command_name not in WRITE_COMMANDS:
        return
    if os.getenv("XADS_ALLOW_WRITES", "").strip().lower() != "true":
        raise BridgeError("write blocked: set XADS_ALLOW_WRITES=true only when you are ready")


def _budget_micro(command: dict[str, Any]) -> int:
    if "amount_local_micro" in command:
        try:
            amount_micro = int(command["amount_local_micro"])
        except (TypeError, ValueError) as exc:
            raise BridgeError("amount_local_micro must be an integer") from exc
    elif "amount_local" in command:
        try:
            amount_micro = int(Decimal(str(command["amount_local"])) * Decimal("1000000"))
        except (InvalidOperation, ValueError) as exc:
            raise BridgeError("amount_local must be numeric") from exc
    else:
        raise BridgeError("set_daily_budget requires amount_local or amount_local_micro")

    if amount_micro <= 0:
        raise BridgeError("daily budget must be greater than zero")

    cap_raw = os.getenv("XADS_MAX_DAILY_BUDGET_LOCAL", "").strip()
    if not cap_raw:
        raise BridgeError("budget write blocked: XADS_MAX_DAILY_BUDGET_LOCAL is not configured")
    try:
        cap_micro = int(Decimal(cap_raw) * Decimal("1000000"))
    except InvalidOperation as exc:
        raise BridgeError("XADS_MAX_DAILY_BUDGET_LOCAL must be numeric") from exc
    if amount_micro > cap_micro:
        raise BridgeError(f"budget write blocked: requested {amount_micro} micro exceeds configured cap {cap_micro}")
    return amount_micro


def execute(command: dict[str, Any]) -> dict[str, Any]:
    name = str(command.get("action", "")).strip()
    if not name:
        raise BridgeError("missing action")

    if name == "ping":
        return {
            "ok": True,
            "bridge": "x-ads-bridge",
            "api_version": API_VERSION,
            "writes_enabled": os.getenv("XADS_ALLOW_WRITES", "").strip().lower() == "true",
        }

    _write_guard(name)

    if name == "list_accounts":
        return _request("GET", "accounts")

    account_id = _account(command)

    if name == "list_campaigns":
        params = {k: command[k] for k in ("cursor", "count", "with_deleted") if k in command}
        return _request("GET", f"accounts/{account_id}/campaigns", params=params)

    if name == "get_campaign":
        campaign_id = str(command.get("campaign_id", "")).strip()
        if not campaign_id:
            raise BridgeError("campaign_id is required")
        return _request("GET", f"accounts/{account_id}/campaigns/{campaign_id}")

    if name == "list_line_items":
        params = {k: command[k] for k in ("campaign_ids", "cursor", "count", "with_deleted") if k in command}
        return _request("GET", f"accounts/{account_id}/line_items", params=params)

    if name == "get_line_item":
        line_item_id = str(command.get("line_item_id", "")).strip()
        if not line_item_id:
            raise BridgeError("line_item_id is required")
        return _request("GET", f"accounts/{account_id}/line_items/{line_item_id}")

    if name == "list_funding_instruments":
        return _request("GET", f"accounts/{account_id}/funding_instruments")

    if name == "stats":
        allowed = (
            "entity",
            "entity_ids",
            "start_time",
            "end_time",
            "granularity",
            "placement",
            "metric_groups",
        )
        params = {k: command[k] for k in allowed if k in command}
        required = ("entity", "entity_ids", "start_time", "end_time", "granularity", "placement", "metric_groups")
        missing = [k for k in required if not params.get(k)]
        if missing:
            raise BridgeError(f"stats missing required fields: {', '.join(missing)}")
        return _request("GET", f"stats/accounts/{account_id}", params=params)

    if name in {"pause_campaign", "resume_campaign"}:
        campaign_id = str(command.get("campaign_id", "")).strip()
        if not campaign_id:
            raise BridgeError("campaign_id is required")
        status = "PAUSED" if name == "pause_campaign" else "ACTIVE"
        return _request("PUT", f"accounts/{account_id}/campaigns/{campaign_id}", data={"entity_status": status})

    if name == "set_daily_budget":
        campaign_id = str(command.get("campaign_id", "")).strip()
        if not campaign_id:
            raise BridgeError("campaign_id is required")
        amount_micro = _budget_micro(command)
        return _request(
            "PUT",
            f"accounts/{account_id}/campaigns/{campaign_id}",
            data={"daily_budget_amount_local_micro": amount_micro},
        )

    if name in {"pause_line_item", "resume_line_item"}:
        line_item_id = str(command.get("line_item_id", "")).strip()
        if not line_item_id:
            raise BridgeError("line_item_id is required")
        status = "PAUSED" if name == "pause_line_item" else "ACTIVE"
        return _request("PUT", f"accounts/{account_id}/line_items/{line_item_id}", data={"entity_status": status})

    raise BridgeError(f"unsupported action: {name}")


def main() -> None:
    raw = os.getenv("XADS_COMMAND", "").strip()
    if not raw:
        raise SystemExit("XADS_COMMAND is required")
    command = json.loads(raw)
    print(json.dumps(execute(command), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
