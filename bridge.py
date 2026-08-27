from __future__ import annotations

import hashlib
import hmac
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
FORMAL_APPROVAL_REQUEST = "正式承認文出してください"
APPROVAL_CODE_LENGTH = 16
PROPOSAL_ID_LENGTH = 12
CONTROL_FIELDS = {
    "approval_token",
    "approval_text",
    "user_approved",
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


def _writes_enabled() -> bool:
    return os.getenv("XADS_ALLOW_WRITES", "").strip().lower() == "true"


def _approval_payload(command: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in command.items() if key not in CONTROL_FIELDS}


def _canonical_payload(command: dict[str, Any]) -> str:
    return json.dumps(
        _approval_payload(command),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _proposal_id(command: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_payload(command).encode("utf-8")).hexdigest()[:PROPOSAL_ID_LENGTH]


def _approval_token(command: dict[str, Any]) -> str:
    # Domain-separated HMAC: changing the X access-token secret invalidates old approvals automatically.
    signing_key = _required_env("XADS_ACCESS_TOKEN_SECRET").encode("utf-8")
    message = ("xads-formal-approval-v1|" + _canonical_payload(command)).encode("utf-8")
    return hmac.new(signing_key, message, hashlib.sha256).hexdigest()[:APPROVAL_CODE_LENGTH]


def _budget_display(command: dict[str, Any]) -> str:
    if "amount_local" in command:
        raw = Decimal(str(command["amount_local"]))
    elif "amount_local_micro" in command:
        raw = Decimal(str(command["amount_local_micro"])) / Decimal("1000000")
    else:
        return "<未指定>"
    normalized = raw.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")


def _approval_description(command: dict[str, Any]) -> str:
    name = str(command.get("action", "")).strip()
    if name == "pause_campaign":
        return f"キャンペーン {str(command.get('campaign_id') or '').strip()} の停止"
    if name == "resume_campaign":
        return f"キャンペーン {str(command.get('campaign_id') or '').strip()} の再開"
    if name == "set_daily_budget":
        campaign_id = str(command.get("campaign_id") or "").strip()
        return f"キャンペーン {campaign_id} の日予算を{_budget_display(command)}円に変更"
    if name == "pause_line_item":
        return f"広告セット {str(command.get('line_item_id') or '').strip()} の停止"
    if name == "resume_line_item":
        return f"広告セット {str(command.get('line_item_id') or '').strip()} の再開"
    return name


def _formal_approval_text(command: dict[str, Any]) -> str:
    token = _approval_token(command)
    description = _approval_description(command)
    return f"正式承認コード {token}：{description}を承認します"


def _issue_formal_approval(command: dict[str, Any]) -> dict[str, Any]:
    proposed = command.get("proposed_command")
    if not isinstance(proposed, dict):
        raise BridgeError("formal approval blocked: proposed_command must be an object")
    action = str(proposed.get("action") or "").strip()
    if action not in WRITE_COMMANDS:
        raise BridgeError("formal approval blocked: proposed_command is not a supported write action")

    request_text = command.get("approval_request_text")
    if request_text != FORMAL_APPROVAL_REQUEST:
        raise BridgeError(
            f"formal approval blocked: approval_request_text must exactly equal '{FORMAL_APPROVAL_REQUEST}'"
        )
    if command.get("da_counter_da_review_complete") is not True:
        raise BridgeError("formal approval blocked: DA/counter-DA review must be marked complete")

    token = _approval_token(proposed)
    return {
        "ok": True,
        "mode": "formal_approval_issued",
        "write_executed": False,
        "proposal_id": _proposal_id(proposed),
        "approval_token": token,
        "approval_code_length": APPROVAL_CODE_LENGTH,
        "formal_approval_text": _formal_approval_text(proposed),
        "approval_text_must_match_exactly": True,
        "proposed_command": _approval_payload(proposed),
        "master_write_switch_enabled": _writes_enabled(),
        "instruction": (
            "Show the formal approval text to the user only now. Execute nothing until the user "
            "copies and returns that exact sentence character-for-character."
        ),
    }


def _write_gate(command: dict[str, Any]) -> dict[str, Any] | None:
    name = str(command.get("action", "")).strip()
    if name not in WRITE_COMMANDS:
        return None

    supplied_token = command.get("approval_token")
    supplied_text = command.get("approval_text")

    # Initial proposal stage: no executable approval data is exposed here.
    if supplied_token is None and supplied_text is None:
        return {
            "ok": True,
            "mode": "proposal",
            "write_executed": False,
            "requires_user_approval": True,
            "requires_da_counter_da_review": True,
            "formal_approval_text_issued": False,
            "proposal_id": _proposal_id(command),
            "proposed_command": _approval_payload(command),
            "master_write_switch_enabled": _writes_enabled(),
            "next_step": (
                f"After DA/counter-DA review and only if the user explicitly says '{FORMAL_APPROVAL_REQUEST}', "
                "request formal approval issuance."
            ),
        }

    if command.get("user_approved") is not True:
        raise BridgeError("approved write blocked: user_approved must be true")
    if not isinstance(supplied_token, str):
        raise BridgeError("approved write blocked: approval_token is required")
    if len(supplied_token) != APPROVAL_CODE_LENGTH:
        raise BridgeError(
            f"approved write blocked: approval_token must be exactly {APPROVAL_CODE_LENGTH} characters"
        )

    expected_token = _approval_token(command)
    if not hmac.compare_digest(supplied_token, expected_token):
        raise BridgeError("approved write blocked: approval_token mismatch; request a fresh formal approval")

    if not isinstance(supplied_text, str):
        raise BridgeError("approved write blocked: approval_text is required")
    expected_text = _formal_approval_text(command)
    # No trimming or normalization: one wrong, missing, or extra character blocks execution.
    if supplied_text != expected_text:
        raise BridgeError(
            "approved write blocked: formal approval sentence mismatch; exact character-for-character approval is required"
        )

    if not _writes_enabled():
        raise BridgeError("approved write blocked: master switch XADS_ALLOW_WRITES is not true")
    return None


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
            "writes_enabled": _writes_enabled(),
            "per_write_user_approval": True,
            "formal_approval_request_required": True,
            "formal_approval_request_text": FORMAL_APPROVAL_REQUEST,
            "exact_approval_text_required": True,
            "approval_code_length": APPROVAL_CODE_LENGTH,
        }

    if name == "issue_write_approval":
        return _issue_formal_approval(command)

    proposal = _write_gate(command)
    if proposal is not None:
        return proposal

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
