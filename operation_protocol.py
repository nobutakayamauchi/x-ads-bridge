from __future__ import annotations

from typing import Any

import bridge


APPROVAL_HASH_REQUEST = "承認ハッシュを発行してください"
APPROVAL_HASH_PREFIX = "XADS-"
EXECUTION_KEY_PREFIX = "RUN-"
EXECUTION_TTL_SECONDS = 300


class OperationProtocolError(RuntimeError):
    pass


def _require_object(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OperationProtocolError(f"{field_name} must be an object")
    return value


def _proposed(command: dict[str, Any]) -> dict[str, Any]:
    proposed = _require_object(command.get("proposed_command"), "proposed_command")
    if not str(proposed.get("action") or "").strip():
        raise OperationProtocolError("proposed_command.action is required")
    return proposed


def _approval_hash(approval_token: str) -> str:
    return f"{APPROVAL_HASH_PREFIX}{approval_token.upper()}"


def _approval_text(approval_token: str) -> str:
    return f"{_approval_hash(approval_token)} で承認"


def _execution_key(execution_token: str) -> str:
    return f"{EXECUTION_KEY_PREFIX}{execution_token.upper()}"


def _execution_text(execution_token: str) -> str:
    return f"{_execution_key(execution_token)} で実行"


def _verify_proposal(
    proposed: dict[str, Any],
    proposal_token: object,
    proposal_expires_at: object,
    *,
    enforce_expiry: bool,
) -> str:
    if not bridge._verify_signed_token(
        proposal_token,
        "proposal",
        proposed,
        expires_at=proposal_expires_at,
        enforce_expiry=enforce_expiry,
    ):
        raise OperationProtocolError("proposal token is invalid, mismatched, or expired")
    if not isinstance(proposal_token, str):
        raise OperationProtocolError("proposal_token is required")
    return proposal_token


def _verify_approval(
    proposed: dict[str, Any],
    proposal_token: str,
    approval_token: object,
    approval_expires_at: object,
    *,
    enforce_expiry: bool,
) -> str:
    if not bridge._verify_signed_token(
        approval_token,
        "approval",
        proposed,
        expires_at=approval_expires_at,
        parent_token=proposal_token,
        enforce_expiry=enforce_expiry,
    ):
        raise OperationProtocolError("approval token is invalid, mismatched, or expired")
    if not isinstance(approval_token, str):
        raise OperationProtocolError("approval_token is required")
    return approval_token


def prepare_proposal(command: dict[str, Any]) -> dict[str, Any]:
    proposed = _proposed(command)
    result = bridge.execute(proposed)
    if result.get("mode") != "proposal":
        raise OperationProtocolError("bridge did not return proposal mode")
    return {
        "ok": True,
        "mode": "proposal_prepared",
        "status": "READY_FOR_CONFIRMATION",
        "write_executed": False,
        "proposed_command": result["proposed_command"],
        "proposal_token": result["proposal_token"],
        "proposal_expires_at": result["proposal_expires_at"],
        "next_step": (
            "After the user confirms the final specification and explicitly asks to issue "
            f"an approval hash, call issue_approval_hash with approval_request_text="
            f"'{APPROVAL_HASH_REQUEST}'."
        ),
    }


def issue_approval_hash(command: dict[str, Any]) -> dict[str, Any]:
    proposed = _proposed(command)
    if command.get("approval_request_text") != APPROVAL_HASH_REQUEST:
        raise OperationProtocolError(
            f"approval_request_text must exactly equal '{APPROVAL_HASH_REQUEST}'"
        )
    if command.get("da_counter_da_review_complete") is not True:
        raise OperationProtocolError("DA/counter-DA review must be complete")

    proposal_token = command.get("proposal_token")
    proposal_expires_at = command.get("proposal_expires_at")
    _verify_proposal(
        proposed,
        proposal_token,
        proposal_expires_at,
        enforce_expiry=True,
    )

    formal = bridge.execute(
        {
            "action": "issue_write_approval",
            "approval_request_text": bridge.FORMAL_APPROVAL_REQUEST,
            "da_counter_da_review_complete": True,
            "proposal_token": proposal_token,
            "proposal_expires_at": proposal_expires_at,
            "proposed_command": proposed,
        }
    )
    approval_token = str(formal["approval_token"])
    return {
        "ok": True,
        "mode": "approval_hash_issued",
        "status": "READY_FOR_APPROVAL",
        "write_executed": False,
        "approval_hash": _approval_hash(approval_token),
        "approval_text_required": _approval_text(approval_token),
        "approval_expires_at": formal["approval_expires_at"],
        "proposal_token": proposal_token,
        "proposal_expires_at": proposal_expires_at,
        "approval_token": approval_token,
        "proposed_command": proposed,
        "warning": "No ad delivery has started. Approval is not execution.",
    }


def confirm_approval(command: dict[str, Any]) -> dict[str, Any]:
    proposed = _proposed(command)
    proposal_token = _verify_proposal(
        proposed,
        command.get("proposal_token"),
        command.get("proposal_expires_at"),
        enforce_expiry=False,
    )
    approval_token = _verify_approval(
        proposed,
        proposal_token,
        command.get("approval_token"),
        command.get("approval_expires_at"),
        enforce_expiry=True,
    )

    approval_text = command.get("approval_text")
    expected = _approval_text(approval_token)
    if approval_text != expected:
        raise OperationProtocolError(
            "approval text mismatch; exact approval hash sentence is required"
        )

    execution_expires_at = bridge._now_epoch() + EXECUTION_TTL_SECONDS
    execution_token = bridge._new_signed_token(
        "execution",
        proposed,
        expires_at=execution_expires_at,
        parent_token=approval_token,
    )
    return {
        "ok": True,
        "mode": "approval_confirmed",
        "status": "APPROVED_NOT_RUNNING",
        "write_executed": False,
        "execution_key": _execution_key(execution_token),
        "execution_text_required": _execution_text(execution_token),
        "execution_token": execution_token,
        "execution_expires_at": execution_expires_at,
        "approval_token": approval_token,
        "approval_expires_at": command.get("approval_expires_at"),
        "proposal_token": proposal_token,
        "proposal_expires_at": command.get("proposal_expires_at"),
        "proposed_command": proposed,
        "warning": "The operation is approved but still not running.",
    }


def execute_approved_operation(command: dict[str, Any]) -> dict[str, Any]:
    proposed = _proposed(command)
    proposal_token = _verify_proposal(
        proposed,
        command.get("proposal_token"),
        command.get("proposal_expires_at"),
        enforce_expiry=False,
    )
    approval_token = _verify_approval(
        proposed,
        proposal_token,
        command.get("approval_token"),
        command.get("approval_expires_at"),
        enforce_expiry=True,
    )

    execution_token = command.get("execution_token")
    execution_expires_at = command.get("execution_expires_at")
    if not bridge._verify_signed_token(
        execution_token,
        "execution",
        proposed,
        expires_at=execution_expires_at,
        parent_token=approval_token,
        enforce_expiry=True,
    ):
        raise OperationProtocolError(
            "execution token is invalid, mismatched, or expired"
        )
    if not isinstance(execution_token, str):
        raise OperationProtocolError("execution_token is required")

    execution_text = command.get("execution_text")
    expected = _execution_text(execution_token)
    if execution_text != expected:
        raise OperationProtocolError(
            "execution text mismatch; exact execution-key sentence is required"
        )

    bridge_command = {
        **proposed,
        "proposal_token": proposal_token,
        "proposal_expires_at": command.get("proposal_expires_at"),
        "approval_token": approval_token,
        "approval_expires_at": command.get("approval_expires_at"),
        "approval_text": bridge._formal_approval_text(proposed, approval_token),
        "user_approved": True,
    }
    result = bridge.execute(bridge_command)
    return {
        "ok": True,
        "mode": "executed",
        "status": "EXECUTED",
        "write_executed": True,
        "proposed_command": proposed,
        "result": result,
    }


def execute(command: dict[str, Any]) -> dict[str, Any]:
    action = str(command.get("action") or "").strip()
    if action == "prepare_proposal":
        return prepare_proposal(command)
    if action == "issue_approval_hash":
        return issue_approval_hash(command)
    if action == "confirm_approval":
        return confirm_approval(command)
    if action == "execute_approved_operation":
        return execute_approved_operation(command)
    raise OperationProtocolError(
        "supported actions: prepare_proposal, issue_approval_hash, "
        "confirm_approval, execute_approved_operation"
    )
