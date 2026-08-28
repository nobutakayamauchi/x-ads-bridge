from __future__ import annotations

import unittest
from unittest.mock import patch

from hypothesis_search import inspect_h1_evidence, run_h1_search


DIRECT_SIGNAL = {
    "source_id": "1",
    "conversation_id": "1",
    "text": "X広告のリンククリック最適化からサイト訪問LPV最適化に切り替えて比較。CPA 12,000円から8,000円に改善した。",
    "created_at": "2026-08-28T00:00:00Z",
    "lang": "ja",
    "public_metrics": {},
}

INDIRECT_SIGNAL = {
    "source_id": "2",
    "conversation_id": "2",
    "text": "X広告でサイト訪問最適化をテスト。CPA 8,000円まで改善した。",
    "created_at": "2026-08-28T00:00:00Z",
    "lang": "ja",
    "public_metrics": {},
}


class HypothesisSearchTests(unittest.TestCase):
    def test_direct_h1_evidence_requires_both_optimization_modes(self):
        result = inspect_h1_evidence(DIRECT_SIGNAL)
        self.assertEqual(result["h1_evidence_class"], "DIRECT")
        self.assertTrue(result["case"]["triad_complete"])
        self.assertTrue(result["eligible_for_h1_store"])

    def test_single_mode_case_is_indirect(self):
        result = inspect_h1_evidence(INDIRECT_SIGNAL)
        self.assertEqual(result["h1_evidence_class"], "INDIRECT")
        self.assertTrue(result["eligible_for_h1_store"])

    @patch("hypothesis_search.search_recent_posts")
    def test_direct_hit_stops_before_fallback(self, search):
        search.return_value = {"result_count": 1, "signals": [DIRECT_SIGNAL]}
        result = run_h1_search()
        self.assertEqual(search.call_count, 1)
        self.assertEqual(result["direct_h1_cases"], 1)
        self.assertEqual([stage["name"] for stage in result["stages"]], ["direct"])

    @patch("hypothesis_search.search_recent_posts")
    def test_fallback_runs_when_direct_query_has_no_direct_case(self, search):
        search.side_effect = [
            {"result_count": 1, "signals": [INDIRECT_SIGNAL]},
            {"result_count": 1, "signals": [DIRECT_SIGNAL]},
        ]
        result = run_h1_search()
        self.assertEqual(search.call_count, 2)
        self.assertEqual(result["direct_h1_cases"], 1)
        self.assertEqual([stage["name"] for stage in result["stages"]], ["direct", "fallback"])
        self.assertLessEqual(result["requested_post_read_cap"], 20)


if __name__ == "__main__":
    unittest.main()
