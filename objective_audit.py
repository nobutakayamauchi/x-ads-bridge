from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

AuditState = Literal[
    "SCALE",
    "HOLD",
    "DIAGNOSE",
    "STOP",
    "INSUFFICIENT_EVIDENCE",
]


@dataclass(frozen=True)
class ObjectiveContract:
    primary_objective: Literal["purchase", "consultation", "lead"]
    target_count: int
    max_spend_jpy: float
    evaluation_window: str
    target_cpa_jpy: float | None = None
    diagnosis_min_x_clicks: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ObjectiveContract":
        required = ("primary_objective", "target_count", "max_spend_jpy", "evaluation_window")
        missing = [key for key in required if value.get(key) in (None, "")]
        if missing:
            raise ValueError(f"objective contract missing: {', '.join(missing)}")

        primary = str(value["primary_objective"])
        if primary not in {"purchase", "consultation", "lead"}:
            raise ValueError("unsupported primary_objective")
        target_count = int(value["target_count"])
        max_spend = float(value["max_spend_jpy"])
        if target_count <= 0:
            raise ValueError("target_count must be > 0")
        if max_spend <= 0:
            raise ValueError("max_spend_jpy must be > 0")

        target_cpa = value.get("target_cpa_jpy")
        if target_cpa is not None:
            target_cpa = float(target_cpa)
            if target_cpa <= 0:
                raise ValueError("target_cpa_jpy must be > 0")

        diagnosis_min = value.get("diagnosis_min_x_clicks")
        if diagnosis_min is not None:
            diagnosis_min = int(diagnosis_min)
            if diagnosis_min <= 0:
                raise ValueError("diagnosis_min_x_clicks must be > 0")

        return cls(
            primary_objective=primary,  # type: ignore[arg-type]
            target_count=target_count,
            max_spend_jpy=max_spend,
            evaluation_window=str(value["evaluation_window"]),
            target_cpa_jpy=target_cpa,
            diagnosis_min_x_clicks=diagnosis_min,
        )


def _objective_count(contract: ObjectiveContract, evidence: dict[str, Any]) -> int:
    if contract.primary_objective == "purchase":
        return int(evidence.get("stripe_paid_purchases", 0) or 0)
    if contract.primary_objective == "consultation":
        return int(evidence.get("stripe_consultation_completions", 0) or 0)
    return int(evidence.get("authoritative_leads", 0) or 0)


def _first_funnel_gap(evidence: dict[str, Any]) -> str | None:
    clicks = int(evidence.get("x_link_clicks", 0) or 0)
    lp = int(evidence.get("lp_unique", 0) or 0)
    consult = int(evidence.get("consult_click_unique", 0) or 0)
    purchase_click = int(evidence.get("purchase_click_unique", 0) or 0)
    consultations = int(evidence.get("stripe_consultation_completions", 0) or 0)
    purchases = int(evidence.get("stripe_paid_purchases", 0) or 0)

    if clicks > 0 and lp == 0:
        return "X clicks exist but owner-excluded LP arrivals are zero"
    if lp > 0 and consult == 0 and purchase_click == 0:
        return "LP arrivals exist but no consultation or purchase CTA progression is observed"
    if consult > 0 and consultations == 0:
        return "consultation CTA clicks exist but no authoritative consultation completion is observed"
    if purchase_click > 0 and purchases == 0:
        return "purchase CTA clicks exist but no authoritative paid purchase is observed"
    return None


def audit_campaign(
    contract_value: dict[str, Any] | None,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(contract_value, dict):
        return {
            "state": "INSUFFICIENT_EVIDENCE",
            "scale_allowed": False,
            "reason": "campaign objective contract is missing",
            "first_funnel_gap": _first_funnel_gap(evidence),
        }

    try:
        contract = ObjectiveContract.from_dict(contract_value)
    except (TypeError, ValueError) as exc:
        return {
            "state": "INSUFFICIENT_EVIDENCE",
            "scale_allowed": False,
            "reason": str(exc),
            "first_funnel_gap": _first_funnel_gap(evidence),
        }

    spend = float(evidence.get("spend_jpy", 0) or 0)
    objective_count = _objective_count(contract, evidence)
    actual_cpa = (spend / objective_count) if objective_count > 0 else None
    gap = _first_funnel_gap(evidence)

    if objective_count >= contract.target_count:
        if contract.target_cpa_jpy is not None and actual_cpa is not None:
            if actual_cpa > contract.target_cpa_jpy:
                state: AuditState = "HOLD"
                reason = "objective target reached, but CPA exceeds the configured target"
            else:
                state = "SCALE"
                reason = "objective target reached inside the configured CPA boundary"
        else:
            state = "SCALE"
            reason = "objective target reached inside the configured spend boundary"
    elif spend >= contract.max_spend_jpy:
        state = "STOP"
        reason = "configured maximum spend reached before the primary objective target"
    else:
        min_clicks = contract.diagnosis_min_x_clicks
        x_clicks = int(evidence.get("x_link_clicks", 0) or 0)
        if gap and min_clicks is not None and x_clicks >= min_clicks:
            state = "DIAGNOSE"
            reason = "configured diagnostic sample reached and a funnel gap is observed"
        else:
            state = "HOLD"
            reason = "objective target not yet reached; stay inside the current bounded test"

    return {
        "state": state,
        "scale_allowed": state == "SCALE",
        "primary_objective": contract.primary_objective,
        "objective_count": objective_count,
        "target_count": contract.target_count,
        "spend_jpy": spend,
        "max_spend_jpy": contract.max_spend_jpy,
        "actual_cpa_jpy": actual_cpa,
        "target_cpa_jpy": contract.target_cpa_jpy,
        "evaluation_window": contract.evaluation_window,
        "first_funnel_gap": gap,
        "reason": reason,
        "invariant": "proxy metrics alone can never authorize SCALE",
    }
