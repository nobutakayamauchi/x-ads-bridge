from __future__ import annotations

from typing import Any

from objective_audit import audit_campaign
from stripe_authority import join_stripe_authority


def audit_with_stripe_authority(
    *,
    objective_contract: dict[str, Any] | None,
    evidence: dict[str, Any],
    stripe_contract: dict[str, Any],
    audited_join_keys: list[dict[str, Any]],
    checkout_sessions: list[dict[str, Any]],
) -> dict[str, Any]:
    authority = join_stripe_authority(
        stripe_contract,
        audited_join_keys,
        checkout_sessions,
    )
    merged = dict(evidence)
    merged["stripe_paid_purchases"] = authority["stripe_paid_purchases"]
    merged["stripe_consultation_completions"] = authority[
        "stripe_consultation_completions"
    ]
    decision = audit_campaign(objective_contract, merged)
    return {
        "ok": True,
        "authority": authority,
        "evidence": merged,
        "decision": decision,
    }
