from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from case_evidence import inspect_case_completeness
from x_signal_collector import search_recent_posts


@dataclass(frozen=True)
class HypothesisSearchSpec:
    hypothesis_id: str
    statement: str
    direct_query: str
    fallback_query: str
    per_query_results: int = 10
    total_post_read_cap: int = 20


H1 = HypothesisSearchSpec(
    hypothesis_id="H1-LPV-VS-LINK-CLICK",
    statement=(
        "For WebAI Bridge, optimizing X Website Traffic for Site Visit/Landing Page View "
        "produces higher-quality website traffic than optimizing for Link Clicks."
    ),
    direct_query=(
        '("X広告" OR "Twitter広告") '
        '("リンククリック" OR "LINK_CLICKS" OR "クリック最適化") '
        '("サイト訪問" OR "LPV" OR "Landing Page View" OR "ランディングページビュー") '
        '(CPA OR CV OR CPC OR "訪問単価" OR 比較 OR テスト OR 改善) lang:ja -is:retweet'
    ),
    fallback_query=(
        '("X広告" OR "Twitter広告") '
        '("サイト訪問" OR "LPV" OR "リンククリック" OR "Webサイト") '
        '(最適化 OR CPA OR CV OR CPC OR 比較 OR テスト OR 改善) lang:ja -is:retweet'
    ),
)

LINK_CLICK_TERMS = (
    "リンククリック",
    "link click",
    "link_clicks",
    "クリック最適化",
)
LPV_TERMS = (
    "サイト訪問",
    "lpv",
    "landing page view",
    "ランディングページビュー",
    "ランディングページ訪問",
)
OUTCOME_TERMS = (
    "cpa",
    "cvr",
    "ctr",
    "cpc",
    "cv",
    "roas",
    "訪問単価",
    "改善",
    "低下",
    "増加",
    "%",
    "％",
    "倍",
)


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(term.casefold() in folded for term in terms)


def inspect_h1_evidence(signal: dict[str, Any]) -> dict[str, Any]:
    text = str(signal.get("text") or "")
    has_link = _has_any(text, LINK_CLICK_TERMS)
    has_lpv = _has_any(text, LPV_TERMS)
    has_outcome = _has_any(text, OUTCOME_TERMS)
    case = inspect_case_completeness({
        **signal,
        "source_type": "operator_post",
    })

    if has_link and has_lpv and has_outcome and case["triad_complete"]:
        h1_class = "DIRECT"
    elif (has_link or has_lpv) and case["complete_legs"] >= 2:
        h1_class = "INDIRECT"
    else:
        h1_class = "IRRELEVANT"

    return {
        "source_id": signal.get("source_id"),
        "conversation_id": signal.get("conversation_id"),
        "created_at": signal.get("created_at"),
        "text": text,
        "public_metrics": signal.get("public_metrics") or {},
        "case": case,
        "h1_evidence_class": h1_class,
        "mentions_link_click_optimization": has_link,
        "mentions_lpv_or_site_visit_optimization": has_lpv,
        "mentions_outcome": has_outcome,
        "eligible_for_h1_store": h1_class in {"DIRECT", "INDIRECT"},
        "scale_authority": False,
    }


def _dedupe(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for signal in signals:
        source_id = str(signal.get("source_id") or "")
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        rows.append(signal)
    return rows


def run_h1_search() -> dict[str, Any]:
    """Run a bounded, hypothesis-first X search.

    Stage 1 looks specifically for direct Link Click vs LPV/Site Visit comparisons.
    Stage 2 runs only when Stage 1 produced no DIRECT evidence. Total requested Post
    reads are capped at 20 (10 + 10), so the configured $0.10 guard remains meaningful.
    """
    stage1 = search_recent_posts(H1.direct_query, max_results=H1.per_query_results)
    raw_signals = list(stage1.get("signals") or [])
    inspected_stage1 = [inspect_h1_evidence(row) for row in raw_signals]
    direct = [row for row in inspected_stage1 if row["h1_evidence_class"] == "DIRECT"]

    stages = [{
        "name": "direct",
        "query": H1.direct_query,
        "result_count": stage1.get("result_count", 0),
    }]

    if not direct:
        stage2 = search_recent_posts(H1.fallback_query, max_results=H1.per_query_results)
        raw_signals.extend(stage2.get("signals") or [])
        stages.append({
            "name": "fallback",
            "query": H1.fallback_query,
            "result_count": stage2.get("result_count", 0),
        })

    deduped = _dedupe(raw_signals)
    inspected = [inspect_h1_evidence(row) for row in deduped]
    direct = [row for row in inspected if row["h1_evidence_class"] == "DIRECT"]
    indirect = [row for row in inspected if row["h1_evidence_class"] == "INDIRECT"]
    irrelevant = [row for row in inspected if row["h1_evidence_class"] == "IRRELEVANT"]
    case_ready = [row for row in inspected if row["case"]["eligible_for_case_store"]]

    return {
        "hypothesis_id": H1.hypothesis_id,
        "statement": H1.statement,
        "requested_post_read_cap": H1.total_post_read_cap,
        "stages": stages,
        "unique_posts": len(inspected),
        "direct_h1_cases": len(direct),
        "indirect_h1_cases": len(indirect),
        "case_ready_posts": len(case_ready),
        "irrelevant_posts": len(irrelevant),
        "evidence": direct + indirect,
        "discarded": irrelevant,
        "decision_rule": (
            "External evidence can prioritize H1 but cannot confirm H1 for WebAI Bridge. "
            "Confirmation/refutation requires the bounded own-campaign LPV experiment."
        ),
    }
