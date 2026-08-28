from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

import requests
from requests_oauthlib import OAuth1

X_API_BASE_URL = os.getenv("X_SIGNAL_API_BASE_URL", "https://api.x.com").rstrip("/")
POST_READ_USD = Decimal("0.005")
DEFAULT_MAX_RESULTS = 20
HARD_MAX_RESULTS = 100


class XSignalError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise XSignalError(f"missing required secret/env: {name}")
    return value


def _auth() -> OAuth1:
    return OAuth1(
        _required_env("XADS_CONSUMER_KEY"),
        _required_env("XADS_CONSUMER_SECRET"),
        _required_env("XADS_ACCESS_TOKEN"),
        _required_env("XADS_ACCESS_TOKEN_SECRET"),
    )


def estimate_post_read_cost_usd(max_results: int) -> Decimal:
    if max_results <= 0 or max_results > HARD_MAX_RESULTS:
        raise XSignalError(f"max_results must be 1..{HARD_MAX_RESULTS}")
    return POST_READ_USD * Decimal(max_results)


def collection_plan(query: str, *, max_results: int = DEFAULT_MAX_RESULTS) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise XSignalError("query is required")
    estimated = estimate_post_read_cost_usd(max_results)
    configured_cap = Decimal(os.getenv("X_SIGNAL_MAX_COST_USD_PER_RUN", "0.10"))
    return {
        "query": query,
        "max_results": max_results,
        "estimated_max_cost_usd": str(estimated),
        "configured_cost_cap_usd": str(configured_cap),
        "within_cost_cap": estimated <= configured_cap,
        "paid_reads_enabled": os.getenv("X_SIGNAL_ALLOW_PAID_READS", "").strip().lower() == "true",
        "privacy_mode": "no user profile lookup; post text/created_at/lang/public_metrics/conversation identity only",
    }


def search_recent_posts(
    query: str,
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
    """Collect a bounded recent-search sample from public X posts.

    This endpoint is pay-per-use. Execution is blocked unless the explicit paid-read switch is enabled.
    """
    plan = collection_plan(query, max_results=max_results)
    if not plan["within_cost_cap"]:
        raise XSignalError(
            f"paid read blocked: estimated ${plan['estimated_max_cost_usd']} exceeds configured cap ${plan['configured_cost_cap_usd']}"
        )
    if not plan["paid_reads_enabled"]:
        raise XSignalError("paid read blocked: X_SIGNAL_ALLOW_PAID_READS must be true")

    params: dict[str, Any] = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,lang,public_metrics,conversation_id,referenced_tweets",
    }
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    response = requests.get(
        f"{X_API_BASE_URL}/2/tweets/search/recent",
        params=params,
        auth=_auth(),
        timeout=45,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text[:4000]}
    if not response.ok:
        raise XSignalError(
            f"X recent search HTTP {response.status_code}: {json.dumps(payload, ensure_ascii=False)[:4000]}"
        )

    rows: list[dict[str, Any]] = []
    for post in payload.get("data") or []:
        rows.append({
            "source_kind": "x_recent_search",
            "source_id": str(post.get("id") or ""),
            "conversation_id": str(post.get("conversation_id") or ""),
            "referenced_tweets": post.get("referenced_tweets") or [],
            "text": str(post.get("text") or ""),
            "created_at": post.get("created_at"),
            "lang": post.get("lang"),
            "public_metrics": post.get("public_metrics") or {},
        })

    return {
        "plan": plan,
        "result_count": len(rows),
        "signals": rows,
        "next_token": (payload.get("meta") or {}).get("next_token"),
        "note": "returned posts are raw candidate signals; inspect hypothesis fit and Intent/Test/Outcome completeness before use",
    }
