from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

TERMINAL_EFFECTIVE_STATUSES = {"COMPLETED", "ENDED", "EXPIRED"}


def _parse_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _reason_texts(line_item: dict[str, Any]) -> list[str]:
    raw = line_item.get("reasons_not_servable") or []
    if not isinstance(raw, list):
        raw = [raw]
    return [str(item).strip().upper() for item in raw if str(item).strip()]


def evaluate_control_completion(
    line_item: dict[str, Any],
    *,
    billed_charge_local_micro: int,
    now: datetime | None = None,
    tolerance_jpy: float = 1.0,
) -> dict[str, Any]:
    """Return manual-check flags only. This function never mutates X Ads state."""

    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    total_budget_micro = int(line_item.get("total_budget_amount_local_micro") or 0)
    billed_micro = max(0, int(billed_charge_local_micro or 0))
    tolerance_micro = max(0, int(float(tolerance_jpy) * 1_000_000))

    remaining_micro = (
        max(total_budget_micro - billed_micro, 0) if total_budget_micro > 0 else None
    )
    budget_exhausted = bool(
        total_budget_micro > 0
        and remaining_micro is not None
        and remaining_micro <= tolerance_micro
    )

    end_at = _parse_time(line_item.get("end_time"))
    end_reached = bool(end_at and now_utc >= end_at)

    effective_status = str(line_item.get("effective_status") or "").strip().upper()
    terminal_status = effective_status in TERMINAL_EFFECTIVE_STATUSES

    reasons = _reason_texts(line_item)
    budget_stop_reason = any("BUDGET" in reason for reason in reasons)
    end_stop_reason = any(
        token in reason
        for reason in reasons
        for token in ("END_TIME", "EXPIRED", "COMPLETED")
    )

    control_closed = bool(
        budget_exhausted
        or budget_stop_reason
        or end_reached
        or end_stop_reason
        or terminal_status
    )
    ready_for_next = control_closed

    reason_codes: list[str] = []
    if budget_exhausted:
        reason_codes.append("BUDGET_EXHAUSTED")
    if budget_stop_reason:
        reason_codes.append("X_BUDGET_STOP_REASON")
    if end_reached:
        reason_codes.append("END_TIME_REACHED")
    if end_stop_reason:
        reason_codes.append("X_END_STOP_REASON")
    if terminal_status:
        reason_codes.append(f"TERMINAL_STATUS_{effective_status}")
    if not reason_codes:
        reason_codes.append("CONTROL_STILL_RUNNING")

    return {
        "BUDGET_EXHAUSTED": budget_exhausted,
        "CONTROL_CLOSED": control_closed,
        "READY_FOR_NEXT": ready_for_next,
        "FLAG": "READY" if ready_for_next else "WAIT",
        "billed_jpy": round(billed_micro / 1_000_000, 2),
        "total_budget_jpy": (
            round(total_budget_micro / 1_000_000, 2) if total_budget_micro > 0 else None
        ),
        "remaining_jpy": (
            round(remaining_micro / 1_000_000, 2)
            if remaining_micro is not None
            else None
        ),
        "entity_status": line_item.get("entity_status"),
        "effective_status": line_item.get("effective_status"),
        "end_time": line_item.get("end_time"),
        "reasons_not_servable": line_item.get("reasons_not_servable") or [],
        "reason_codes": reason_codes,
        "read_only": True,
    }
