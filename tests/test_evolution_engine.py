from __future__ import annotations

import unittest
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


class EvolutionEngineTests(unittest.TestCase):
    def test_high_relevance_signal_enters_hypothesis_pool(self):
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
        self.assertEqual(result["relevance_band"], "HIGH")
        self.assertTrue(result["eligible_for_hypothesis_pool"])
        self.assertFalse(result["scale_authority"])
        self.assertIn("GPTs", result["matched_topics"])
        self.assertIn("creative_hook", result["hypothesis_dimensions"])

    def test_low_relevance_signal_is_rejected(self):
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
        self.assertEqual(result["relevance_band"], "LOW")
        self.assertFalse(result["eligible_for_hypothesis_pool"])

    def test_aggregate_and_nominate_hypotheses(self):
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
        self.assertEqual(metadata["eligible_signals"], 2)
        self.assertTrue(hypotheses)
        self.assertTrue(all(item["requires_one_variable_test"] for item in hypotheses))

    def test_diagnostic_win_does_not_authorize_scale(self):
        meaning = classify_experiment_meaning(
            {"state": "DIAGNOSE", "scale_allowed": False},
            {
                "sample_reached": True,
                "hypothesis_resolution": "refuted",
                "changed_variables": ["optimization_event"],
            },
        )
        self.assertEqual(meaning["meaning_class"], "DIAGNOSTIC_WIN")
        self.assertTrue(meaning["meaningful"])
        self.assertFalse(meaning["scale_allowed"])

    def test_business_win_authorizes_scale_only_when_audit_allows_it(self):
        meaning = classify_experiment_meaning(
            {"state": "SCALE", "scale_allowed": True},
            {
                "sample_reached": True,
                "hypothesis_resolution": "confirmed",
                "changed_variables": ["creative_hook"],
            },
        )
        self.assertEqual(meaning["meaning_class"], "BUSINESS_WIN")
        self.assertTrue(meaning["scale_allowed"])

    def test_multi_variable_test_cannot_be_diagnostic_win(self):
        meaning = classify_experiment_meaning(
            {"state": "STOP", "scale_allowed": False},
            {
                "sample_reached": True,
                "hypothesis_resolution": "confirmed",
                "changed_variables": ["creative_hook", "targeting"],
            },
        )
        self.assertEqual(meaning["meaning_class"], "BUSINESS_LOSS")
        self.assertFalse(meaning["meaningful"])

    def test_next_experiment_skips_tested_dimension(self):
        candidate = next_experiment_candidate(
            [
                {"dimension": "creative_hook", "candidate": "集客"},
                {"dimension": "offer_or_cta", "candidate": "相談"},
            ],
            ["creative_hook"],
        )
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate["dimension"], "offer_or_cta")


if __name__ == "__main__":
    unittest.main()
