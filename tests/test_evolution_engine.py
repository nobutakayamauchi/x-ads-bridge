from __future__ import annotations

from datetime import datetime, timezone

from evolution_engine import (
    aggregate_signal_metadata,
    classify_experiment_meaning,
    inspect_external_signal,
    next_experiment_candidate,
    nominate_hypotheses,
)


PROFILE = {
    "product_id": "webai-bridge",
    "market": "Japan",
    "language": "ja",
    "price_jpy": 98000,
    "topics": ["GPTs", "ChatGPT", "生成AI", "AIツール", "WebAI"],
    "pain_terms": ["販売", "配布", "集客", "Knowledge", "導入"],
    "intent_terms": ["買う", "購入", "相談", "販売", "導入"],
    "offer_terms": ["無料相談", "モニター", "診断"],
}


def test_high_relevance_signal_enters_hypothesis_pool():
    result = inspect_external_signal(
        {
            "source_kind": "x_recent_search",
            "source_id": "123",
            "text": "GPTsが配布できないので生成AIツールの販売と導入を相談したい",
            "lang": "ja",
            "created_at": "2026-08-28T00:00:00Z",
            "public_metrics": {"like_count": 10, "reply_count": 2, "retweet_count": 1, "quote_count": 0},
        },
        PROFILE,
        now=datetime(2026, 8, 28, 0, 30, tzinfo=timezone.utc),
    )
    assert result["relevance_band"] == "HIGH"
    assert result["eligible_for_hypothesis_pool"] is True
    assert result["scale_authority"] is False
    assert "GPTs" in result["matched_topics"]
    assert "creative_hook" in result["hypothesis_dimensions"]


def test_low_relevance_signal_is_rejected():
    result = inspect_external_signal(
        {
            "source_kind": "x_recent_search",
            "source_id": "999",
            "text": "今日の晩ごはんはカレー",
            "lang": "ja",
            "created_at": "2026-08-28T00:00:00Z",
        },
        PROFILE,
        now=datetime(2026, 8, 28, 0, 30, tzinfo=timezone.utc),
    )
    assert result["relevance_band"] == "LOW"
    assert result["eligible_for_hypothesis_pool"] is False


def test_aggregate_and_nominate_hypotheses():
    inspected = [
        inspect_external_signal(
            {
                "source_kind": "public_case_study",
                "source_id": "case-1",
                "text": "GPTs 配布 販売 導入 相談",
                "lang": "ja",
                "created_at": "2026-08-27T00:00:00Z",
                "metrics": {"spend": 5000, "clicks": 100, "conversions": 4, "cpa": 1250},
            },
            PROFILE,
            now=datetime(2026, 8, 28, tzinfo=timezone.utc),
        ),
        inspect_external_signal(
            {
                "source_kind": "x_recent_search",
                "source_id": "post-1",
                "text": "ChatGPT AIツールを販売したいが集客に困る",
                "lang": "ja",
                "created_at": "2026-08-28T00:00:00Z",
                "public_metrics": {"like_count": 1, "reply_count": 1, "retweet_count": 0, "quote_count": 0},
            },
            PROFILE,
            now=datetime(2026, 8, 28, tzinfo=timezone.utc),
        ),
    ]
    metadata = aggregate_signal_metadata(inspected)
    hypotheses = nominate_hypotheses(metadata)
    assert metadata["eligible_signals"] == 2
    assert hypotheses
    assert all(item["requires_one_variable_test"] for item in hypotheses)


def test_diagnostic_win_does_not_authorize_scale():
    meaning = classify_experiment_meaning(
        {"state": "DIAGNOSE", "scale_allowed": False},
        {
            "sample_reached": True,
            "hypothesis_resolution": "refuted",
            "changed_variables": ["optimization_event"],
        },
    )
    assert meaning["meaning_class"] == "DIAGNOSTIC_WIN"
    assert meaning["meaningful"] is True
    assert meaning["scale_allowed"] is False


def test_business_win_authorizes_scale_only_when_audit_allows_it():
    meaning = classify_experiment_meaning(
        {"state": "SCALE", "scale_allowed": True},
        {
            "sample_reached": True,
            "hypothesis_resolution": "confirmed",
            "changed_variables": ["creative_hook"],
        },
    )
    assert meaning["meaning_class"] == "BUSINESS_WIN"
    assert meaning["scale_allowed"] is True


def test_multi_variable_test_cannot_be_diagnostic_win():
    meaning = classify_experiment_meaning(
        {"state": "STOP", "scale_allowed": False},
        {
            "sample_reached": True,
            "hypothesis_resolution": "confirmed",
            "changed_variables": ["creative_hook", "targeting"],
        },
    )
    assert meaning["meaning_class"] == "BUSINESS_LOSS"
    assert meaning["meaningful"] is False


def test_next_experiment_skips_tested_dimension():
    candidate = next_experiment_candidate(
        [
            {"dimension": "creative_hook", "candidate": "集客"},
            {"dimension": "offer_or_cta", "candidate": "相談"},
        ],
        ["creative_hook"],
    )
    assert candidate is not None
    assert candidate["dimension"] == "offer_or_cta"
