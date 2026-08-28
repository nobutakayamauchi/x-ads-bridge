from __future__ import annotations

from typing import Any


class CampaignFactoryError(ValueError):
    pass


def _micro(jpy: int) -> int:
    if isinstance(jpy, bool) or int(jpy) <= 0:
        raise CampaignFactoryError("budget JPY must be greater than zero")
    return int(jpy) * 1_000_000


def build_paused_site_visits_plan(
    *,
    campaign_name: str,
    line_item_name: str,
    funding_instrument_id: str,
    start_time: str,
    end_time: str,
    daily_budget_jpy: int,
    total_budget_jpy: int,
    tweet_ids: list[str],
    targeting: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the exact X Ads API payloads for the H1 one-variable experiment.

    Safety/causal invariants:
    - everything is created PAUSED
    - parent campaign uses LINE_ITEM budget optimization
    - line item keeps WEBSITE_CLICKS/AUTO/ALL_ON_TWITTER
    - the only optimization change vs control is goal=SITE_VISITS
    - primary_web_event_tag is intentionally omitted because X requires it for
      WEBSITE_CONVERSIONS, not SITE_VISITS
    - activation is a separate approval-gated operation
    """
    if not campaign_name.strip() or not line_item_name.strip():
        raise CampaignFactoryError("campaign and line item names are required")
    if not funding_instrument_id.strip():
        raise CampaignFactoryError("funding_instrument_id is required")
    if not start_time.strip() or not end_time.strip():
        raise CampaignFactoryError("start_time and end_time are required")
    if total_budget_jpy < daily_budget_jpy:
        raise CampaignFactoryError("total budget must be >= daily budget")
    clean_tweet_ids = [str(value).strip() for value in tweet_ids if str(value).strip()]
    if not clean_tweet_ids:
        raise CampaignFactoryError("at least one tweet_id is required")
    if not targeting:
        raise CampaignFactoryError("targeting must not be empty")

    normalized_targeting: list[dict[str, Any]] = []
    for criterion in targeting:
        targeting_type = str(criterion.get("targeting_type") or "").strip()
        targeting_value = str(criterion.get("targeting_value") or "").strip()
        operator_type = str(criterion.get("operator_type") or "EQ").strip()
        if not targeting_type or not targeting_value:
            raise CampaignFactoryError("every targeting criterion needs type and value")
        normalized_targeting.append({
            "targeting_type": targeting_type,
            "targeting_value": targeting_value,
            "operator_type": operator_type,
        })

    return {
        "mode": "PREPARE_PAUSED_ONLY",
        "activation_allowed": False,
        "changed_variable": "goal: LINK_CLICKS -> SITE_VISITS",
        "campaign": {
            "funding_instrument_id": funding_instrument_id,
            "name": campaign_name,
            "budget_optimization": "LINE_ITEM",
            "entity_status": "PAUSED",
        },
        "line_item": {
            "name": line_item_name,
            "objective": "WEBSITE_CLICKS",
            "goal": "SITE_VISITS",
            "product_type": "PROMOTED_TWEETS",
            "placements": "ALL_ON_TWITTER",
            "bid_strategy": "AUTO",
            "pay_by": "IMPRESSION",
            "entity_status": "PAUSED",
            "standard_delivery": True,
            "start_time": start_time,
            "end_time": end_time,
            "daily_budget_amount_local_micro": _micro(daily_budget_jpy),
            "total_budget_amount_local_micro": _micro(total_budget_jpy),
        },
        "targeting_criteria": normalized_targeting,
        "promoted_tweets": {
            "tweet_ids": clean_tweet_ids,
        },
        "post_create_invariants": [
            "campaign.entity_status == PAUSED",
            "line_item.entity_status == PAUSED",
            "line_item.objective == WEBSITE_CLICKS",
            "line_item.goal == SITE_VISITS",
            "line_item.bid_strategy == AUTO",
            "line_item.placements contains ALL_ON_TWITTER",
            "no primary_web_event_tag is introduced",
            "activation requires a separate approval-gated resume action after control completion",
        ],
    }
