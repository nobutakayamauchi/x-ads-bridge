from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Callable


class CampaignBundleError(ValueError):
    pass


RequestFn = Callable[..., dict[str, Any]]


def _required_text(command: dict[str, Any], key: str) -> str:
    value = str(command.get(key) or "").strip()
    if not value:
        raise CampaignBundleError(f"{key} is required")
    return value


def _positive_jpy(command: dict[str, Any], key: str) -> Decimal:
    raw = command.get(key)
    if isinstance(raw, bool):
        raise CampaignBundleError(f"{key} must be numeric")
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError) as exc:
        raise CampaignBundleError(f"{key} must be numeric") from exc
    if value <= 0:
        raise CampaignBundleError(f"{key} must be greater than zero")
    return value


def _micro(value: Decimal) -> int:
    return int(value * Decimal("1000000"))


def _response_id(payload: dict[str, Any], label: str) -> str:
    data = payload.get("data")
    if isinstance(data, dict):
        value = str(data.get("id") or "").strip()
        if value:
            return value
    raise CampaignBundleError(f"{label} response did not contain data.id")


def _entity_data(payload: dict[str, Any], label: str) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise CampaignBundleError(f"{label} response did not contain data object")
    return data


def _targeting(command: dict[str, Any]) -> list[dict[str, str]]:
    raw = command.get("targeting")
    if not isinstance(raw, list) or not raw:
        raise CampaignBundleError("targeting must be a non-empty list")
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise CampaignBundleError("each targeting item must be an object")
        targeting_type = str(item.get("targeting_type") or "").strip()
        targeting_value = str(item.get("targeting_value") or "").strip()
        operator_type = str(item.get("operator_type") or "EQ").strip()
        if not targeting_type or not targeting_value:
            raise CampaignBundleError("targeting_type and targeting_value are required")
        if operator_type not in {"EQ", "NE", "GTE", "LT"}:
            raise CampaignBundleError("invalid targeting operator_type")
        out.append(
            {
                "targeting_type": targeting_type,
                "targeting_value": targeting_value,
                "operator_type": operator_type,
            }
        )
    return out


def _tweet_ids(command: dict[str, Any]) -> list[str]:
    raw = command.get("tweet_ids")
    if not isinstance(raw, list):
        raise CampaignBundleError("tweet_ids must be a list")
    values = [str(value).strip() for value in raw if str(value).strip()]
    if not values:
        raise CampaignBundleError("at least one tweet_id is required")
    if len(values) > 50:
        raise CampaignBundleError("tweet_ids cannot exceed 50")
    return values


def normalized_creation_plan(command: dict[str, Any]) -> dict[str, Any]:
    goal = str(command.get("goal") or "SITE_VISITS").strip()
    if goal not in {"SITE_VISITS", "LINK_CLICKS"}:
        raise CampaignBundleError("goal must be SITE_VISITS or LINK_CLICKS")

    daily = _positive_jpy(command, "daily_budget_jpy")
    total = _positive_jpy(command, "total_budget_jpy")
    if total < daily:
        raise CampaignBundleError("total_budget_jpy must be >= daily_budget_jpy")

    return {
        "funding_instrument_id": _required_text(command, "funding_instrument_id"),
        "campaign_name": _required_text(command, "campaign_name"),
        "line_item_name": _required_text(command, "line_item_name"),
        "start_time": _required_text(command, "start_time"),
        "end_time": _required_text(command, "end_time"),
        "daily_budget_jpy": daily,
        "total_budget_jpy": total,
        "goal": goal,
        "tweet_ids": _tweet_ids(command),
        "targeting": _targeting(command),
    }


def create_paused_website_traffic_bundle(
    *, account_id: str, command: dict[str, Any], request_fn: RequestFn
) -> dict[str, Any]:
    plan = normalized_creation_plan(command)
    created: dict[str, Any] = {
        "campaign_id": None,
        "line_item_id": None,
        "targeting_criterion_ids": [],
        "promoted_tweet_ids": [],
    }

    try:
        campaign_response = request_fn(
            "POST",
            f"accounts/{account_id}/campaigns",
            data={
                "funding_instrument_id": plan["funding_instrument_id"],
                "name": plan["campaign_name"],
                "budget_optimization": "LINE_ITEM",
                "entity_status": "PAUSED",
            },
        )
        campaign_id = _response_id(campaign_response, "campaign")
        created["campaign_id"] = campaign_id

        line_item_response = request_fn(
            "POST",
            f"accounts/{account_id}/line_items",
            data={
                "campaign_id": campaign_id,
                "name": plan["line_item_name"],
                "objective": "WEBSITE_CLICKS",
                "goal": plan["goal"],
                "product_type": "PROMOTED_TWEETS",
                "placements": "ALL_ON_TWITTER",
                "bid_strategy": "AUTO",
                "pay_by": "IMPRESSION",
                "entity_status": "PAUSED",
                "standard_delivery": True,
                "start_time": plan["start_time"],
                "end_time": plan["end_time"],
                "daily_budget_amount_local_micro": _micro(plan["daily_budget_jpy"]),
                "total_budget_amount_local_micro": _micro(plan["total_budget_jpy"]),
            },
        )
        line_item_id = _response_id(line_item_response, "line item")
        created["line_item_id"] = line_item_id

        for criterion in plan["targeting"]:
            response = request_fn(
                "POST",
                f"accounts/{account_id}/targeting_criteria",
                data={"line_item_id": line_item_id, **criterion},
            )
            created["targeting_criterion_ids"].append(
                _response_id(response, "targeting criterion")
            )

        promoted_response = request_fn(
            "POST",
            f"accounts/{account_id}/promoted_tweets",
            data={
                "line_item_id": line_item_id,
                "tweet_ids": ",".join(plan["tweet_ids"]),
            },
        )
        promoted_data = promoted_response.get("data")
        if not isinstance(promoted_data, list) or not promoted_data:
            raise CampaignBundleError("promoted_tweets response did not contain data list")
        for item in promoted_data:
            if isinstance(item, dict) and str(item.get("id") or "").strip():
                created["promoted_tweet_ids"].append(str(item["id"]).strip())
        if not created["promoted_tweet_ids"]:
            raise CampaignBundleError("promoted_tweets response contained no IDs")

        read_back = {
            "campaign": request_fn(
                "GET", f"accounts/{account_id}/campaigns/{campaign_id}"
            ),
            "line_item": request_fn(
                "GET", f"accounts/{account_id}/line_items/{line_item_id}"
            ),
            "targeting": request_fn(
                "GET",
                f"accounts/{account_id}/targeting_criteria",
                params={"line_item_ids": line_item_id, "count": 1000},
            ),
            "promoted_tweets": request_fn(
                "GET",
                f"accounts/{account_id}/promoted_tweets",
                params={"line_item_ids": line_item_id, "count": 1000},
            ),
        }
        campaign_data = _entity_data(read_back["campaign"], "campaign read-back")
        line_item_data = _entity_data(read_back["line_item"], "line-item read-back")
        if str(campaign_data.get("entity_status")) != "PAUSED":
            raise CampaignBundleError("campaign read-back is not PAUSED")
        if str(line_item_data.get("entity_status")) != "PAUSED":
            raise CampaignBundleError("line-item read-back is not PAUSED")

        return {
            "ok": True,
            "mode": "PAUSED_BUNDLE_CREATED",
            "write_executed": True,
            "delivery_started": False,
            "created": created,
            "read_back": read_back,
            "next_step": "Activation requires a separate approved activate_campaign_bundle operation.",
        }
    except Exception as exc:  # report partial state; never auto-delete/rollback
        return {
            "ok": False,
            "mode": "PARTIAL_OR_FAILED_PAUSED_BUNDLE_CREATION",
            "write_executed": any(
                [created["campaign_id"], created["line_item_id"], created["targeting_criterion_ids"], created["promoted_tweet_ids"]]
            ),
            "delivery_started": False,
            "created": created,
            "error": f"{type(exc).__name__}: {exc}",
            "rollback_performed": False,
            "instruction": "Inspect created IDs. Do not auto-delete. Repair or explicitly remove only after human review.",
        }


def activate_campaign_bundle(
    *, account_id: str, command: dict[str, Any], request_fn: RequestFn
) -> dict[str, Any]:
    campaign_id = _required_text(command, "campaign_id")
    line_item_id = _required_text(command, "line_item_id")

    campaign_before = request_fn(
        "GET", f"accounts/{account_id}/campaigns/{campaign_id}"
    )
    line_before = request_fn(
        "GET", f"accounts/{account_id}/line_items/{line_item_id}"
    )
    campaign_data = _entity_data(campaign_before, "campaign")
    line_data = _entity_data(line_before, "line item")

    if str(line_data.get("campaign_id") or "") != campaign_id:
        raise CampaignBundleError("line item does not belong to the requested campaign")
    if str(campaign_data.get("entity_status")) != "PAUSED":
        raise CampaignBundleError("campaign must be PAUSED immediately before activation")
    if str(line_data.get("entity_status")) != "PAUSED":
        raise CampaignBundleError("line item must be PAUSED immediately before activation")

    campaign_resumed = False
    try:
        request_fn(
            "PUT",
            f"accounts/{account_id}/campaigns/{campaign_id}",
            data={"entity_status": "ACTIVE"},
        )
        campaign_resumed = True
        request_fn(
            "PUT",
            f"accounts/{account_id}/line_items/{line_item_id}",
            data={"entity_status": "ACTIVE"},
        )
    except Exception as exc:
        return {
            "ok": False,
            "mode": "PARTIAL_ACTIVATION",
            "write_executed": campaign_resumed,
            "campaign_resumed": campaign_resumed,
            "line_item_resumed": False,
            "error": f"{type(exc).__name__}: {exc}",
            "safety_note": "If campaign resume succeeded but line-item resume failed, the PAUSED line item prevents delivery.",
        }

    campaign_after = request_fn(
        "GET", f"accounts/{account_id}/campaigns/{campaign_id}"
    )
    line_after = request_fn(
        "GET", f"accounts/{account_id}/line_items/{line_item_id}"
    )
    campaign_after_data = _entity_data(campaign_after, "campaign read-back")
    line_after_data = _entity_data(line_after, "line-item read-back")
    active = (
        str(campaign_after_data.get("entity_status")) == "ACTIVE"
        and str(line_after_data.get("entity_status")) == "ACTIVE"
    )
    return {
        "ok": active,
        "mode": "BUNDLE_ACTIVE" if active else "ACTIVATION_READBACK_MISMATCH",
        "write_executed": True,
        "delivery_may_start": active,
        "campaign": campaign_after,
        "line_item": line_after,
    }
