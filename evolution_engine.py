from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

RelevanceBand = Literal["HIGH", "MEDIUM", "LOW"]
MeaningClass = Literal[
    "BUSINESS_WIN",
    "DIAGNOSTIC_WIN",
    "BUSINESS_LOSS",
    "INCONCLUSIVE",
]


@dataclass(frozen=True)
class ProductProfile:
    product_id: str
    market: str
    language: str
    price_jpy: float | None
    topics: tuple[str, ...]
    pain_terms: tuple[str, ...]
    intent_terms: tuple[str, ...]
    offer_terms: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProductProfile":
        required = ("product_id", "market", "language", "topics", "pain_terms", "intent_terms")
        missing = [key for key in required if value.get(key) in (None, "")]
        if missing:
            raise ValueError(f"product profile missing: {', '.join(missing)}")
        return cls(
            product_id=str(value["product_id"]),
            market=str(value["market"]),
            language=str(value["language"]),
            price_jpy=float(value["price_jpy"]) if value.get("price_jpy") is not None else None,
            topics=tuple(str(x) for x in value.get("topics", [])),
            pain_terms=tuple(str(x) for x in value.get("pain_terms", [])),
            intent_terms=tuple(str(x) for x in value.get("intent_terms", [])),
            offer_terms=tuple(str(x) for x in value.get("offer_terms", [])),
        )


def _match_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.casefold()
    return [term for term in terms if term.casefold() in lowered]


def _ratio(matches: list[str], terms: tuple[str, ...]) -> float:
    if not terms:
        return 0.0
    return min(1.0, len(set(matches)) / min(4, len(terms)))


def _freshness_score(collected_at: str | None, now: datetime | None = None) -> float:
    if not collected_at:
        return 0.5
    now = now or datetime.now(timezone.utc)
    try:
        observed = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.5
    age_days = max(0.0, (now - observed).total_seconds() / 86400)
    if age_days <= 2:
        return 1.0
    if age_days <= 7:
        return 0.8
    if age_days <= 30:
        return 0.55
    return 0.25


def _evidence_quality(raw: dict[str, Any]) -> float:
    source_kind = str(raw.get("source_kind") or "public_post")
    if source_kind == "own_campaign":
        return 1.0
    if source_kind in {"public_case_study", "expert_case"}:
        metrics = raw.get("metrics") or {}
        useful = sum(1 for key in ("spend", "impressions", "clicks", "conversions", "cpa", "roas") if metrics.get(key) is not None)
        return min(1.0, 0.55 + useful * 0.075)
    if source_kind in {"x_recent_search", "x_filtered_stream", "public_post"}:
        public_metrics = raw.get("public_metrics") or {}
        engagement_fields = sum(1 for key in ("like_count", "reply_count", "retweet_count", "quote_count") if public_metrics.get(key) is not None)
        return min(0.75, 0.35 + engagement_fields * 0.08)
    return 0.3


def inspect_external_signal(
    raw: dict[str, Any],
    product_value: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Inspect one external signal and convert it into product-specific metadata.

    External data can nominate hypotheses, but it never authorizes SCALE.
    """
    profile = ProductProfile.from_dict(product_value)
    text = str(raw.get("text") or "")
    topic_matches = _match_terms(text, profile.topics)
    pain_matches = _match_terms(text, profile.pain_terms)
    intent_matches = _match_terms(text, profile.intent_terms)
    offer_matches = _match_terms(text, profile.offer_terms)

    source_lang = str(raw.get("lang") or "")
    market_score = 1.0 if source_lang == profile.language else (0.65 if not source_lang else 0.25)
    topic_score = _ratio(topic_matches, profile.topics)
    pain_score = _ratio(pain_matches, profile.pain_terms)
    intent_score = _ratio(intent_matches, profile.intent_terms)
    offer_score = _ratio(offer_matches, profile.offer_terms) if profile.offer_terms else 0.5
    evidence_score = _evidence_quality(raw)
    freshness = _freshness_score(str(raw.get("created_at") or raw.get("collected_at") or ""), now=now)

    score = round(
        0.30 * topic_score
        + 0.18 * pain_score
        + 0.17 * intent_score
        + 0.10 * market_score
        + 0.08 * offer_score
        + 0.10 * evidence_score
        + 0.07 * freshness,
        4,
    )
    if score >= 0.72:
        band: RelevanceBand = "HIGH"
    elif score >= 0.48:
        band = "MEDIUM"
    else:
        band = "LOW"

    hypothesis_dimensions: list[str] = []
    if topic_matches:
        hypothesis_dimensions.append("targeting_or_message_topic")
    if pain_matches:
        hypothesis_dimensions.append("creative_hook")
    if intent_matches:
        hypothesis_dimensions.append("offer_or_cta")
    if raw.get("metrics"):
        hypothesis_dimensions.append("benchmark")

    return {
        "source_kind": str(raw.get("source_kind") or "public_post"),
        "source_id": str(raw.get("source_id") or raw.get("id") or ""),
        "product_id": profile.product_id,
        "relevance_score": score,
        "relevance_band": band,
        "matched_topics": sorted(set(topic_matches)),
        "matched_pains": sorted(set(pain_matches)),
        "matched_intents": sorted(set(intent_matches)),
        "matched_offers": sorted(set(offer_matches)),
        "evidence_quality": round(evidence_score, 3),
        "freshness_score": round(freshness, 3),
        "hypothesis_dimensions": hypothesis_dimensions,
        "eligible_for_hypothesis_pool": band in {"HIGH", "MEDIUM"},
        "scale_authority": False,
        "privacy_mode": "aggregate_features_only",
    }


def aggregate_signal_metadata(inspected: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in inspected if row.get("eligible_for_hypothesis_pool")]
    topics: Counter[str] = Counter()
    pains: Counter[str] = Counter()
    intents: Counter[str] = Counter()
    dimensions: Counter[str] = Counter()
    weighted_score = 0.0

    for row in eligible:
        weight = float(row.get("relevance_score", 0) or 0)
        weighted_score += weight
        for value in row.get("matched_topics", []):
            topics[str(value)] += 1
        for value in row.get("matched_pains", []):
            pains[str(value)] += 1
        for value in row.get("matched_intents", []):
            intents[str(value)] += 1
        for value in row.get("hypothesis_dimensions", []):
            dimensions[str(value)] += 1

    def top(counter: Counter[str], n: int = 8) -> list[dict[str, Any]]:
        return [{"value": value, "count": count} for value, count in counter.most_common(n)]

    return {
        "total_signals": len(inspected),
        "eligible_signals": len(eligible),
        "mean_relevance": round(weighted_score / len(eligible), 4) if eligible else 0.0,
        "top_topics": top(topics),
        "top_pains": top(pains),
        "top_intents": top(intents),
        "candidate_dimensions": top(dimensions, n=5),
        "use_rule": "external signals may nominate one-variable experiments but can never authorize SCALE",
    }


def nominate_hypotheses(metadata: dict[str, Any], *, max_candidates: int = 5) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for row in metadata.get("top_pains", [])[:2]:
        candidates.append({
            "dimension": "creative_hook",
            "candidate": row["value"],
            "support_count": row["count"],
            "status": "CANDIDATE",
            "requires_one_variable_test": True,
        })
    for row in metadata.get("top_intents", [])[:1]:
        candidates.append({
            "dimension": "offer_or_cta",
            "candidate": row["value"],
            "support_count": row["count"],
            "status": "CANDIDATE",
            "requires_one_variable_test": True,
        })
    for row in metadata.get("top_topics", [])[:2]:
        candidates.append({
            "dimension": "targeting_or_message_topic",
            "candidate": row["value"],
            "support_count": row["count"],
            "status": "CANDIDATE",
            "requires_one_variable_test": True,
        })
    return candidates[:max_candidates]


def classify_experiment_meaning(
    objective_audit: dict[str, Any],
    diagnostic: dict[str, Any],
) -> dict[str, Any]:
    """Separate commercial success from useful experimental learning."""
    state = str(objective_audit.get("state") or "INSUFFICIENT_EVIDENCE")
    sample_reached = bool(diagnostic.get("sample_reached"))
    resolution = str(diagnostic.get("hypothesis_resolution") or "unresolved")
    changed_variables = diagnostic.get("changed_variables") or []
    one_variable = len(changed_variables) == 1

    if state == "SCALE":
        meaning: MeaningClass = "BUSINESS_WIN"
        meaningful = True
        reason = "primary business objective reached inside the configured boundary"
    elif sample_reached and one_variable and resolution in {"confirmed", "refuted"}:
        meaning = "DIAGNOSTIC_WIN"
        meaningful = True
        reason = "bounded one-variable test resolved a hypothesis even though SCALE is not authorized"
    elif state == "STOP" and sample_reached:
        meaning = "BUSINESS_LOSS"
        meaningful = False
        reason = "spend boundary was reached without business success or a resolved diagnostic hypothesis"
    else:
        meaning = "INCONCLUSIVE"
        meaningful = False
        reason = "not enough controlled evidence to call the ad commercially or diagnostically meaningful"

    return {
        "meaning_class": meaning,
        "meaningful": meaningful,
        "business_state": state,
        "scale_allowed": bool(objective_audit.get("scale_allowed")) and meaning == "BUSINESS_WIN",
        "hypothesis_resolution": resolution,
        "one_variable_test": one_variable,
        "reason": reason,
        "invariant": "external X signals and proxy metrics cannot authorize SCALE",
    }


def next_experiment_candidate(
    hypotheses: list[dict[str, Any]],
    tested_dimensions: list[str],
) -> dict[str, Any] | None:
    tested = set(tested_dimensions)
    for hypothesis in hypotheses:
        dimension = str(hypothesis.get("dimension") or "")
        if dimension and dimension not in tested:
            return {
                **hypothesis,
                "experiment_rule": "change exactly this dimension; freeze creative/LP/targeting/bid/optimization fields not under test",
            }
    return None
