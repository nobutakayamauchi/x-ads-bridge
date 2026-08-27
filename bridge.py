from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
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
    "set_line_item_daily_budget",
}

FORMAL_APPROVAL_REQUEST = "正式承認文出してください"
TOKEN_LENGTH = 16
TOKEN_NONCE_LENGTH = 6
CONTROL_FIELDS = {
    "proposal_token",
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


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        raise BridgeError(
            f"X Ads API {response.status_code}: "
            f"{json.dumps(payload, ensure_ascii=False)[:4000]}"
        )
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


def _signing_key() -> bytes:
    return _required_env("XADS_ACCESS_TOKEN_SECRET").encode("utf-8")


def _token_signature(
    kind: str,
    command: dict[str, Any],
    nonce: str,
    *,
    parent_token: str = "",
) -> str:
    message = (
        f"xads-{kind}-v3|{nonce}|{parent_token}|{_canonical_payload(command)}"
    ).encode("utf-8")
    digest = hmac.new(_signing_key(), message, hashlib.sha256).hexdigest()
    return digest[: TOKEN_LENGTH - TOKEN_NONCE_LENGTH]


def _new_signed_token(
    kind: str,
    command: dict[str, Any],
    *,
    parent_token: str = "",
) -> str:
    nonce = secrets.token_hex(TOKEN_NONCE_LENGTH // 2)
    return nonce + _token_signature(
        kind,
        command,
        nonce,
        parent_token=parent_token,
    )


def _verify_signed_token(
    token: object,
    kind: str,
    command: dict[str, Any],
    *,
    parent_token: str = "",
) -> bool:
    if not isinstance(token, str) or len(token) != TOKEN_LENGTH:
        return False
    try:
        int(token, 16)
    except ValueError:
        return False
    nonce = token[:TOKEN_NONCE_LENGTH]
    expected = nonce + _token_signature(
        kind,
        command,
        nonce,
        parent_token=parent_token,
    )
    return hmac.compare_digest(token, expected)


def _decimal_amount(command: dict[str, Any]) -> Decimal:
    if "amount_local" in command:
        raw = command["amount_local"]
    elif "amount_local_micro" in command:
        try:
            return Decimal(str(command["amount_local_micro"])) / Decimal("1000000")
        except InvalidOperation as exc:
            raise BridgeError("amount_local_micro must be numeric") from exc
    else:
        raise BridgeError("budget change requires amount_local or amount_local_micro")

    try:
        return Decimal(str(raw))
    except InvalidOperation as exc:
        raise BridgeError("amount_local must be numeric") from exc


def _budget_display(command: dict[str, Any]) -> str:
    raw = _decimal_amount(command)
    normalized = raw.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")


def _budget_micro(command: dict[str, Any]) -> int:
    amount = _decimal_amount(command)
    amount_micro = int(amount * Decimal("1000000"))
    if amount_micro <= 0:
        raise BridgeError("daily budget must be greater than zero")

    cap_raw = os.getenv("XADS_MAX_DAILY_BUDGET_LOCAL", "").strip()
    if not cap_raw:
        raise BridgeError(
            "budget write blocked: XADS_MAX_DAILY_BUDGET_LOCAL is not configured"
        )
    try:
        cap_micro = int(Decimal(cap_raw) * Decimal("1000000"))
    except InvalidOperation as exc:
        raise BridgeError("XADS_MAX_DAILY_BUDGET_LOCAL must be numeric") from exc
    if amount_micro > cap_micro:
        raise BridgeError(
            f"budget write blocked: requested {amount_micro} micro "
            f"exceeds configured cap {cap_micro}"
        )
    return amount_micro


def _validate_write_shape(command: dict[str, Any]) -> None:
    name = str(command.get("action", "")).strip()
    if name not in WRITE_COMMANDS:
        raise BridgeError(f"unsupported write action: {name or '<missing>'}")

    _account(command)

    if name in {"pause_campaign", "resume_campaign", "set_daily_budget"}:
        if not str(command.get("campaign_id") or "").strip():
            raise BridgeError("campaign_id is required")

    if name in {
        "pause_line_item",
        "resume_line_item",
        "set_line_item_daily_budget",
    }:
        if not str(command.get("line_item_id") or "").strip():
            raise BridgeError("line_item_id is required")

    if name in {"set_daily_budget", "set_line_item_daily_budget"}:
        if _decimal_amount(command) <= 0:
            raise BridgeError("daily budget must be greater than zero")


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
    if name == "set_line_item_daily_budget":
        line_item_id = str(command.get("line_item_id") or "").strip()
        return f"広告セット {line_item_id} の日予算を{_budget_display(command)}円に変更"
    return name


def _formal_approval_text(command: dict[str, Any], approval_token: str) -> str:
    return (
        f"正式承認コード {approval_token}："
        f"{_approval_description(command)}を承認します"
    )


def _write_account_guard(command: dict[str, Any]) -> None:
    configured = os.getenv("XADS_ACCOUNT_ID", "").strip()
    if not configured:
        raise BridgeError(
            "approved write blocked: XADS_ACCOUNT_ID must be configured to pin writes "
            "to one ads account"
        )
    requested = _account(command)
    if requested != configured:
        raise BridgeError(
            "approved write blocked: account_id does not match pinned XADS_ACCOUNT_ID"
        )


def _execution_event_guard() -> None:
    event_action = os.getenv("XADS_EVENT_ACTION", "").strip().lower()
    if event_action and event_action != "opened":
        raise BridgeError(
            "approved write blocked: execution is allowed only from a newly opened issue; "
            "reopened issues cannot execute writes"
        )


def _issue_formal_approval(command: dict[str, Any]) -> dict[str, Any]:
    proposed = command.get("proposed_command")
    if not isinstance(proposed, dict):
        raise BridgeError("formal approval blocked: proposed_command must be an object")
    _validate_write_shape(proposed)

    if command.get("approval_request_text") != FORMAL_APPROVAL_REQUEST:
        raise BridgeError(
            f"formal approval blocked: approval_request_text must exactly equal "
            f"'{FORMAL_APPROVAL_REQUEST}'"
        )
    if command.get("da_counter_da_review_complete") is not True:
        raise BridgeError(
            "formal approval blocked: DA/counter-DA review must be marked complete"
        )

    proposal_token = command.get("proposal_token")
    if not _verify_signed_token(proposal_token, "proposal", proposed):
        raise BridgeError(
            "formal approval blocked: proposal_token mismatch or invalid; "
            "request a fresh proposal"
        )

    assert isinstance(proposal_token, str)
    approval_token = _new_signed_token(
        "approval",
        proposed,
        parent_token=proposal_token,
    )
    return {
        "ok": True,
        "mode": "formal_approval_issued",
        "write_executed": False,
        "proposal_token_verified": True,
        "proposal_token": proposal_token,
        "approval_token": approval_token,
        "approval_code_length": TOKEN_LENGTH,
        "formal_approval_text": _formal_approval_text(proposed, approval_token),
        "approval_text_must_match_exactly": True,
        "proposed_command": _approval_payload(proposed),
        "master_write_switch_enabled": _writes_enabled(),
        "write_account_pinned": bool(os.getenv("XADS_ACCOUNT_ID", "").strip()),
        "instruction": (
            "The proposal token was verified and the approval token is bound to it. "
            "Show the formal approval sentence to the user. Execute nothing until the user "
            "copies and returns that exact sentence character-for-character."
        ),
    }


def is_execution_attempt(command: dict[str, Any]) -> bool:
    name = str(command.get("action", "")).strip()
    if name not in WRITE_COMMANDS:
        return False
    return any(
        key in command
        for key in ("proposal_token", "approval_token", "approval_text", "user_approved")
    )


def _write_gate(command: dict[str, Any]) -> dict[str, Any] | None:
    name = str(command.get("action", "")).strip()
    if name not in WRITE_COMMANDS:
        return None

    _validate_write_shape(command)

    proposal_token = command.get("proposal_token")
    approval_token = command.get("approval_token")
    approval_text = command.get("approval_text")

    # Stage 1: proposal only. No executable approval data is issued.
    if (
        proposal_token is None
        and approval_token is None
        and approval_text is None
        and command.get("user_approved") is None
    ):
        fresh_proposal_token = _new_signed_token("proposal", command)
        return {
            "ok": True,
            "mode": "proposal",
            "write_executed": False,
            "requires_user_approval": True,
            "requires_da_counter_da_review": True,
            "formal_approval_text_issued": False,
            "proposal_token": fresh_proposal_token,
            "proposal_token_length": TOKEN_LENGTH,
            "proposed_command": _approval_payload(command),
            "master_write_switch_enabled": _writes_enabled(),
            "write_account_pinned": bool(os.getenv("XADS_ACCOUNT_ID", "").strip()),
            "next_step": (
                f"After DA/counter-DA review and only if the user explicitly says "
                f"'{FORMAL_APPROVAL_REQUEST}', submit this exact proposal together with "
                "proposal_token to request a fresh formal approval token."
            ),
        }

    # Stage 3: execution. Both tokens and the exact sentence must validate.
    if command.get("user_approved") is not True:
        raise BridgeError("approved write blocked: user_approved must be true")
    if not _verify_signed_token(proposal_token, "proposal", command):
        raise BridgeError(
            "approved write blocked: proposal_token mismatch or invalid; "
            "request a fresh proposal"
        )
    if not isinstance(proposal_token, str):
        raise BridgeError("approved write blocked: proposal_token is required")
    if not _verify_signed_token(
        approval_token,
        "approval",
        command,
        parent_token=proposal_token,
    ):
        raise BridgeError(
            "approved write blocked: approval_token mismatch, invalid, or not bound "
            "to this proposal_token"
        )
    if not isinstance(approval_token, str):
        raise BridgeError("approved write blocked: approval_token is required")
    if not isinstance(approval_text, str):
        raise BridgeError("approved write blocked: approval_text is required")

    expected_text = _formal_approval_text(command, approval_token)
    # Deliberately no trim/normalization. One missing/extra/different character blocks it.
    if approval_text != expected_text:
        raise BridgeError(
            "approved write blocked: formal approval sentence mismatch; "
            "exact character-for-character approval is required"
        )

    _execution_event_guard()
    _write_account_guard(command)
    if not _writes_enabled():
        raise BridgeError(
            "approved write blocked: master switch XADS_ALLOW_WRITES is not true"
        )
    return None


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
            "proposal_token_required": True,
            "formal_approval_token_required": True,
            "approval_token_bound_to_proposal_token": True,
            "formal_approval_request_required": True,
            "formal_approval_request_text": FORMAL_APPROVAL_REQUEST,
            "exact_approval_text_required": True,
            "approval_code_length": TOKEN_LENGTH,
            "reopened_write_execution_blocked": True,
            "write_account_pinned": bool(os.getenv("XADS_ACCOUNT_ID", "").strip()),
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
        params = {
            k: command[k]
            for k in ("cursor", "count", "with_deleted")
            if k in command
        }
        return _request("GET", f"accounts/{account_id}/campaigns", params=params)

    if name == "get_campaign":
        campaign_id = str(command.get("campaign_id", "")).strip()
        if not campaign_id:
            raise BridgeError("campaign_id is required")
        return _request("GET", f"accounts/{account_id}/campaigns/{campaign_id}")

    if name == "list_line_items":
        params = {
            k: command[k]
            for k in ("campaign_ids", "cursor", "count", "with_deleted")
            if k in command
        }
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
        required = (
            "entity",
            "entity_ids",
            "start_time",
            "end_time",
            "granularity",
            "placement",
            "metric_groups",
        )
        missing = [k for k in required if not params.get(k)]
        if missing:
            raise BridgeError(
                f"stats missing required fields: {', '.join(missing)}"
            )
        return _request("GET", f"stats/accounts/{account_id}", params=params)

    if name in {"pause_campaign", "resume_campaign"}:
        campaign_id = str(command.get("campaign_id", "")).strip()
        status = "PAUSED" if name == "pause_campaign" else "ACTIVE"
        return _request(
            "PUT",
            f"accounts/{account_id}/campaigns/{campaign_id}",
            data={"entity_status": status},
        )

    if name == "set_daily_budget":
        campaign_id = str(command.get("campaign_id", "")).strip()
        amount_micro = _budget_micro(command)
        return _request(
            "PUT",
            f"accounts/{account_id}/campaigns/{campaign_id}",
            data={"daily_budget_amount_local_micro": amount_micro},
        )

    if name in {"pause_line_item", "resume_line_item"}:
        line_item_id = str(command.get("line_item_id", "")).strip()
        status = "PAUSED" if name == "pause_line_item" else "ACTIVE"
        return _request(
            "PUT",
            f"accounts/{account_id}/line_items/{line_item_id}",
            data={"entity_status": status},
        )

    if name == "set_line_item_daily_budget":
        line_item_id = str(command.get("line_item_id", "")).strip()
        amount_micro = _budget_micro(command)
        return _request(
            "PUT",
            f"accounts/{account_id}/line_items/{line_item_id}",
            data={"daily_budget_amount_local_micro": amount_micro},
        )

    raise BridgeError(f"unsupported action: {name}")


def main() -> None:
    raw = os.getenv("XADS_COMMAND", "").strip()
    if not raw:
        raise SystemExit("XADS_COMMAND is required")
    command = json.loads(raw)
    print(json.dumps(execute(command), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
