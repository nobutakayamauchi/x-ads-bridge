from __future__ import annotations

import re
from typing import Any

INTENT_TERMS = ("目的", "狙", "獲得", "改善", "検証", "増や", "下げ", "上げ")
TEST_TERMS = ("A/B", "AB", "テスト", "変更", "比較", "切り替", "ターゲティング", "LP", "クリエイティブ", "最適化", "入札")
OUTCOME_TERMS = ("CPA", "CV", "CVR", "CTR", "CPC", "CPM", "ROAS", "売上", "問い合わせ", "%", "％", "倍", "低下", "増加", "改善")
METRIC_RE = re.compile(r"(?i)(CPA|CVR|CTR|CPC|CPM|ROAS|CV|売上|問い合わせ)[^\n]{0,32}?(\d[\d,.]*\s*(?:%|％|円|件|倍)?)")


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(term.casefold() in folded for term in terms)


def inspect_case_completeness(raw: dict[str, Any]) -> dict[str, Any]:
    """Classify whether a public item/thread can become reusable experiment evidence.

    This is intentionally conservative: popularity is ignored. A reusable case needs
    reconstructable Intent -> Test -> Outcome evidence.
    """
    text = str(raw.get("text") or "")
    intent = _has_any(text, INTENT_TERMS) or bool(raw.get("intent"))
    test = _has_any(text, TEST_TERMS) or bool(raw.get("test"))
    outcome = _has_any(text, OUTCOME_TERMS) or bool(raw.get("outcome"))
    metric_matches = [{"metric": m.group(1), "value": m.group(2)} for m in METRIC_RE.finditer(text)]
    quantitative = bool(metric_matches) or bool((raw.get("outcome") or {}).get("metrics"))

    legs = {"intent": intent, "test": test, "outcome": outcome}
    complete_count = sum(1 for value in legs.values() if value)
    self_reported = str(raw.get("source_type") or "operator_post") not in {"official_case", "audited_report"}

    if complete_count == 3:
        case_class = "CASE_READY_SELF_REPORTED" if self_reported else "CASE_READY_VERIFIED"
    elif complete_count in {1, 2}:
        case_class = "PARTIAL_CASE"
    else:
        case_class = "ANECDOTE"

    return {
        "case_class": case_class,
        "triad": legs,
        "triad_complete": complete_count == 3,
        "complete_legs": complete_count,
        "quantitative_outcome": quantitative,
        "metric_mentions": metric_matches,
        "eligible_for_case_store": complete_count == 3,
        "eligible_for_hypothesis_pool": complete_count >= 2,
        "scale_authority": False,
        "rule": "external cases can prioritize hypotheses; only own authoritative outcome evidence can authorize SCALE",
    }


def merge_thread_parts(parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Join Posts from one coherent thread/conversation before triad inspection."""
    if not parts:
        return inspect_case_completeness({"text": ""})
    conversation_ids = {str(p.get("conversation_id") or "") for p in parts if p.get("conversation_id")}
    coherent = len(conversation_ids) <= 1
    merged_text = "\n".join(str(p.get("text") or "") for p in parts)
    result = inspect_case_completeness({
        "text": merged_text,
        "source_type": parts[0].get("source_type") or "operator_post",
    })
    result["thread_coherent"] = coherent
    result["part_count"] = len(parts)
    if not coherent:
        result["case_class"] = "REJECTED"
        result["eligible_for_case_store"] = False
    return result
