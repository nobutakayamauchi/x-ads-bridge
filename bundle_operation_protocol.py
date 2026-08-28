from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Any

import bridge
from campaign_bundle import (
    CampaignBundleError,
    activate_campaign_bundle,
    create_paused_website_traffic_bundle,
    normalized_creation_plan,
)


APPROVAL_HASH_REQUEST = "承認ハッシュを発行してください"
APPROVAL_HASH_PREFIX = "XADS-"
EXECUTION_KEY_PREFIX = "RUN-"
PROPOSAL_TTL_SECONDS = 3600
APPROVAL_TTL_SECONDS = 900
EXECUTION_TTL_SECONDS = 300
SUPPORTED_BUNDLE_ACTIONS = {
    "create_website_traffic_bundle_paused",
    "activate_campaign_bundle",
}


class BundleOperationError(RuntimeError):
    pass


def _required_object(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BundleOperationError(f"{name} must be an object")
    return value


def _proposed(command: dict[str, Any]) -> dict[str, Any]:
    proposed = _required_object(command.get("proposed_command"), "proposed_command")
    action = str(proposed.get("action") or "").strip()
    if action not in SUPPORTED_BUNDLE_ACTIONS:
        raise BundleOperationError(
            "proposed_command.action must be create_website_traffic_bundle_paused "
            "or activate_campaign_bundle"
        )
    _validate_proposed(proposed)
    return proposed


def _account(command: dict[str, Any]) -> str:
    account_id = str(command.get("account_id") or bridge.DEFAULT_ACCOUNT_ID).strip()
    if not account_id:
        raise BundleOperationError("account_id is required")
    return account_id


def _decimal_env(name: str) -> Decimal:
    raw = os.getenv(name, "").strip()
    if not raw:
        raise BundleOperationError(f"{name} must be configured")
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise BundleOperationError(f"{name} must be numeric") from exc
    if value <= 0:
        raise BundleOperationError(f"{name} must be greater than zero")
    return value


def _validate_budget_caps(command: dict[str, Any]) -> None:
    plan = normalized_creation_plan(command)
    daily_cap = _decimal_env("XADS_MAX_DAILY_BUDGET_LOCAL")
    total_cap = _decimal_env("XADS_MAX_TOTAL_BUDGET_LOCAL")
    if plan["daily_budget_jpy"] > daily_cap:
        raise BundleOperationError(
            f"daily budget {plan['daily_budget_jpy']} exceeds configured cap {daily_cap}"
        )
    if plan["total_budget_jpy"] > total_cap:
        raise BundleOperationError(
            f"total budget {plan['total_budget_jpy']} exceeds configured cap {total_cap}"
        )


def _validate_proposed(command: dict[str, Any]) -> None:
    _account(command)
    action = str(command.get("action") or "").strip()
    if action == "create_website_traffic_bundle_paused":
        normalized_creation_plan(command)
        _validate_budget_caps(command)
    elif action == "activate_campaign_bundle":
        if not str(command.get("campaign_id") or "").strip():
            raise BundleOperationError("campaign_id is required")
        if not str(command.get("line_item_id") or "").strip():
            raise BundleOperationError("line_item_id is required")


def _approval_hash(token: str) -> str:
    return f"{APPROVAL_HASH_PREFIX}{token.upper()}"


def _approval_text(token: str) -> str:
    return f"{_approval_hash(token)} で承認"


def _execution_key(token: str) -> str:
    return f"{EXECUTION_KEY_PREFIX}{token.upper()}"


def _execution_text(token: str) -> str:
    return f"{_execution_key(token)} で実行"


def _new_token(kind: str, proposed: dict[str, Any], expires_at: int, parent: str = "") -> str:
    return bridge._new_signed_token(
        kind,
        proposed,
        expires_at=expires_at,
        parent_token=parent,
    )


def _verify_token(
    token: object,
    kind: str,
    proposed: dict[str, Any],
    expires_at: object,
    *,
    parent: str = "",
    enforce_expiry: bool = True,
) -> str:
    if not bridge._verify_signed_token(
        token,
        kind,
        proposed,
        expires_at=expires_at,
        parent_token=parent,
        enforce_expiry=enforce_expiry,
    ):
        raise BundleOperationError(f"{kind} token invalid, mismatched, or expired")
    if not isinstance(token, str):
        raise BundleOperationError(f"{kind} token is required")
    return token


def prepare_bundle_proposal(command: dict[str, Any]) -> dict[str, Any]:
    proposed = _proposed(command)
    expires_at = bridge._now_epoch() + PROPOSAL_TTL_SECONDS
    token = _new_token("bundle-proposal", proposed, expires_at)
    return {
        "ok": True,
        "mode": "bundle_proposal_prepared",
        "status": "READY_FOR_CONFIRMATION",
        "write_executed": False,
        "delivery_started": False,
        "proposed_command": proposed,
        "proposal_token": token,
        "proposal_expires_at": expires_at,
        "next_step": (
            "After final spec/preview confirmation and DA/counter-DA review, request an "
            f"approval hash with exact text '{APPROVAL_HASH_REQUEST}'."
        ),
    }


def issue_bundle_approval_hash(command: dict[str, Any]) -> dict[str, Any]:
    proposed = _proposed(command)
    if command.get("approval_request_text") != APPROVAL_HASH_REQUEST:
        raise BundleOperationError(
            f"approval_request_text must exactly equal '{APPROVAL_HASH_REQUEST}'"
        )
    if command.get("da_counter_da_review_complete") is not True:
        raise BundleOperationError("DA/counter-DA review must be complete")

    proposal_token = _verify_token(
        command.get("proposal_token"),
        "bundle-proposal",
        proposed,
        command.get("proposal_expires_at"),
        enforce_expiry=True,
    )
    approval_expires_at = bridge._now_epoch() + APPROVAL_TTL_SECONDS
    approval_token = _new_token(
        "bundle-approval", proposed, approval_expires_at, proposal_token
    )
    return {
        "ok": True,
        "mode": "bundle_approval_hash_issued",
        "status": "READY_FOR_APPROVAL",
        "write_executed": False,
        "delivery_started": False,
        "approval_hash": _approval_hash(approval_token),
        "approval_text_required": _approval_text(approval_token),
        "approval_token": approval_token,
        "approval_expires_at": approval_expires_at,
        "proposal_token": proposal_token,
        "proposal_expires_at": command.get("proposal_expires_at"),
        "proposed_command": proposed,
        "warning": "Approval is not execution. No X Ads write has occurred.",
    }


def confirm_bundle_approval(command: dict[str, Any]) -> dict[str, Any]:
    proposed = _proposed(command)
    proposal_token = _verify_token(
        command.get("proposal_token"),
        "bundle-proposal",
        proposed,
        command.get("proposal_expires_at"),
        enforce_expiry=False,
    )
    approval_token = _verify_token(
        command.get("approval_token"),
        "bundle-approval",
        proposed,
        command.get("approval_expires_at"),
        parent=proposal_token,
        enforce_expiry=True,
    )
    if command.get("approval_text") != _approval_text(approval_token):
        raise BundleOperationError("exact approval-hash sentence is required")

    execution_expires_at = bridge._now_epoch() + EXECUTION_TTL_SECONDS
    execution_token = _new_token(
        "bundle-execution", proposed, execution_expires_at, approval_token
    )
    return {
        "ok": True,
        "mode": "bundle_approval_confirmed",
        "status": "APPROVED_NOT_RUNNING",
        "write_executed": False,
        "delivery_started": False,
        "execution_key": _execution_key(execution_token),
        "execution_text_required": _execution_text(execution_token),
        "execution_token": execution_token,
        "execution_expires_at": execution_expires_at,
        "approval_token": approval_token,
        "approval_expires_at": command.get("approval_expires_at"),
        "proposal_token": proposal_token,
        "proposal_expires_at": command.get("proposal_expires_at"),
        "proposed_command": proposed,
        "warning": "Approved, but still not running.",
    }


def _execution_guards(proposed: dict[str, Any]) -> None:
    bridge._execution_event_guard()
    bridge._write_account_guard(proposed)
    if not bridge._writes_enabled():
        raise BundleOperationError("XADS_ALLOW_WRITES is not true")


def _cap_micro(value: object, cap_env: str, label: str) -> None:
    if value is None:
        raise BundleOperationError(f"{label} is missing on the line item")
    try:
        jpy = Decimal(str(value)) / Decimal("1000000")
    except InvalidOperation as exc:
        raise BundleOperationError(f"{label} is not numeric") from exc
    cap = _decimal_env(cap_env)
    if jpy > cap:
        raise BundleOperationError(f"{label} {jpy} exceeds configured cap {cap}")


def _validate_activation_caps(account_id: str, line_item_id: str) -> None:
    payload = bridge._request("GET", f"accounts/{account_id}/line_items/{line_item_id}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise BundleOperationError("line item read-back missing data object")
    _cap_micro(
        data.get("daily_budget_amount_local_micro"),
        "XADS_MAX_DAILY_BUDGET_LOCAL",
        "daily budget",
    )
    _cap_micro(
        data.get("total_budget_amount_local_micro"),
        "XADS_MAX_TOTAL_BUDGET_LOCAL",
        "total budget",
    )


def execute_approved_bundle(command: dict[str, Any]) -> dict[str, Any]:
    proposed = _proposed(command)
    proposal_token = _verify_token(
        command.get("proposal_token"),
        "bundle-proposal",
        proposed,
        command.get("proposal_expires_at"),
        enforce_expiry=False,
    )
    approval_token = _verify_token(
        command.get("approval_token"),
        "bundle-approval",
        proposed,
        command.get("approval_expires_at"),
        parent=proposal_token,
        enforce_expiry=True,
    )
    execution_token = _verify_token(
        command.get("execution_token"),
        "bundle-execution",
        proposed,
        command.get("execution_expires_at"),
        parent=approval_token,
        enforce_expiry=True,
    )
    if command.get("execution_text") != _execution_text(execution_token):
        raise BundleOperationError("exact execution-key sentence is required")

    _execution_guards(proposed)
    account_id = _account(proposed)
    action = str(proposed["action"])
    if action == "create_website_traffic_bundle_paused":
        _validate_budget_caps(proposed)
        result = create_paused_website_traffic_bundle(
            account_id=account_id,
            command=proposed,
            request_fn=bridge._request,
        )
    else:
        line_item_id = str(proposed["line_item_id"])
        _validate_activation_caps(account_id, line_item_id)
        result = activate_campaign_bundle(
            account_id=account_id,
            command=proposed,
            request_fn=bridge._request,
        )

    return {
        "ok": bool(result.get("ok")),
        "mode": "bundle_executed",
        "status": "EXECUTED",
        "write_executed": bool(result.get("write_executed")),
        "proposed_command": proposed,
        "result": result,
    }


def execute(command: dict[str, Any]) -> dict[str, Any]:
    action = str(command.get("action") or "").strip()
    try:
        if action == "prepare_bundle_proposal":
            return prepare_bundle_proposal(command)
        if action == "issue_bundle_approval_hash":
            return issue_bundle_approval_hash(command)
        if action == "confirm_bundle_approval":
            return confirm_bundle_approval(command)
        if action == "execute_approved_bundle":
            return execute_approved_bundle(command)
    except CampaignBundleError as exc:
        raise BundleOperationError(str(exc)) from exc
    raise BundleOperationError(
        "supported actions: prepare_bundle_proposal, issue_bundle_approval_hash, "
        "confirm_bundle_approval, execute_approved_bundle"
    )
