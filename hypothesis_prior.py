from __future__ import annotations

from collections import Counter
from typing import Any


SUPPORT = "SUPPORTS_H1"
REFUTE = "REFUTES_H1"


def _source_family(case: dict[str, Any]) -> str:
    explicit = str(case.get("source_family") or "").strip()
    if explicit:
        return explicit
    kind = str(case.get("source_kind") or "")
    if kind.startswith("official_x_"):
        return "x_official"
    if kind == "x_recent_search":
        return "x_operator_posts"
    return kind or "unknown"


def _bias_multiplier(case: dict[str, Any]) -> float:
    flags = set((case.get("verification") or {}).get("bias_flags") or [])
    multiplier = 1.0
    if "platform_success_story_selection_bias" in flags:
        multiplier *= 0.75
    if "x_funded_advertiser_test" in flags:
        multiplier *= 0.85
    if "platform_product_test" in flags:
        multiplier *= 0.78
    if "product_launch_period" in flags or "2021_2022_product_launch_period" in flags:
        multiplier *= 0.9
    if "absolute_budget_not_disclosed" in flags or "participant_and_budget_details_not_disclosed" in flags:
        multiplier *= 0.95
    return round(multiplier, 4)


def score_external_case(case: dict[str, Any]) -> dict[str, Any]:
    verification = case.get("verification") or {}
    product_fit = case.get("product_fit") or {}
    strength = max(0.0, min(1.0, float(verification.get("evidence_strength", 0.5) or 0.5)))
    fit = max(0.0, min(1.0, float(product_fit.get("score", 0.0) or 0.0)))
    bias = _bias_multiplier(case)
    direct_multiplier = 1.0 if case.get("h1_evidence_class") == "DIRECT" else 0.55
    weight = strength * fit * bias * direct_multiplier
    direction = str(case.get("direction") or "UNKNOWN")
    signed = weight if direction == SUPPORT else (-weight if direction == REFUTE else 0.0)
    return {
        "case_id": case.get("case_id"),
        "source_family": _source_family(case),
        "direction": direction,
        "h1_evidence_class": case.get("h1_evidence_class"),
        "evidence_strength": round(strength, 4),
        "product_fit": round(fit, 4),
        "bias_multiplier": bias,
        "weight": round(weight, 6),
        "signed_weight": round(signed, 6),
        "scale_authority": False,
    }


def build_directional_prior(cases: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [score_external_case(case) for case in cases]
    usable = [row for row in scored if row["weight"] > 0 and row["direction"] in {SUPPORT, REFUTE}]
    total_weight = sum(row["weight"] for row in usable)
    signed_weight = sum(row["signed_weight"] for row in usable)
    directional_score = (signed_weight / total_weight) if total_weight else 0.0
    families = Counter(row["source_family"] for row in usable)
    direct_count = sum(1 for row in usable if row["h1_evidence_class"] == "DIRECT")
    support_count = sum(1 for row in usable if row["direction"] == SUPPORT)
    refute_count = sum(1 for row in usable if row["direction"] == REFUTE)
    independent_families = len(families)

    # This is deliberately not a Bayesian probability. Correlated success stories must
    # not turn into false confidence simply because several pages repeat the same platform view.
    if directional_score >= 0.6:
        if direct_count >= 2 and independent_families >= 2:
            prior_class = "STRONG_DIRECTIONAL_SUPPORT"
        else:
            prior_class = "MODERATE_DIRECTIONAL_SUPPORT_INDEPENDENCE_LIMITED"
    elif directional_score >= 0.2:
        prior_class = "MODERATE_DIRECTIONAL_SUPPORT"
    elif directional_score <= -0.6:
        if direct_count >= 2 and independent_families >= 2:
            prior_class = "STRONG_DIRECTIONAL_REFUTATION"
        else:
            prior_class = "MODERATE_DIRECTIONAL_REFUTATION_INDEPENDENCE_LIMITED"
    elif directional_score <= -0.2:
        prior_class = "MODERATE_DIRECTIONAL_REFUTATION"
    else:
        prior_class = "MIXED_OR_WEAK"

    return {
        "prior_class": prior_class,
        "directional_score": round(directional_score, 4),
        "note": "directional_score is an evidence-priority score, not a probability",
        "usable_cases": len(usable),
        "direct_cases": direct_count,
        "support_cases": support_count,
        "refute_cases": refute_count,
        "independent_source_families": independent_families,
        "source_families": dict(families),
        "independence_limited": independent_families < 2,
        "case_scores": scored,
        "recommended_action": "Run the bounded WebAI Bridge one-variable LPV-vs-Link-Click experiment; external evidence cannot confirm or SCALE the campaign.",
        "scale_authority": False,
    }
