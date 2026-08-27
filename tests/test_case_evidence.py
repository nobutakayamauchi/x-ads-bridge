from __future__ import annotations

import unittest

from case_evidence import inspect_case_completeness, merge_thread_parts


class CaseEvidenceTests(unittest.TestCase):
    def test_complete_self_reported_case(self):
        result = inspect_case_completeness({
            "source_type": "operator_post",
            "text": "CPA改善を狙ってLPをA/Bテスト。LPを広告専用に変更した結果、CPAが12000円から7000円に低下した。",
        })
        self.assertTrue(result["triad_complete"])
        self.assertEqual(result["case_class"], "CASE_READY_SELF_REPORTED")
        self.assertTrue(result["quantitative_outcome"])
        self.assertFalse(result["scale_authority"])

    def test_partial_post_is_not_stored_as_case(self):
        result = inspect_case_completeness({"text": "X広告はLPを分けた方がいいと思う"})
        self.assertFalse(result["triad_complete"])
        self.assertFalse(result["eligible_for_case_store"])

    def test_thread_can_complete_triad(self):
        result = merge_thread_parts([
            {"conversation_id": "abc", "text": "問い合わせ獲得を増やすのが目的でした。"},
            {"conversation_id": "abc", "text": "そこでターゲティングを広げるテストを実施。"},
            {"conversation_id": "abc", "text": "結果CPAが30%低下しCVが2倍になった。"},
        ])
        self.assertTrue(result["triad_complete"])
        self.assertTrue(result["thread_coherent"])

    def test_mixed_threads_are_rejected(self):
        result = merge_thread_parts([
            {"conversation_id": "a", "text": "CPA改善が目的"},
            {"conversation_id": "b", "text": "LPを変更してCPA30%低下"},
        ])
        self.assertEqual(result["case_class"], "REJECTED")
        self.assertFalse(result["eligible_for_case_store"])


if __name__ == "__main__":
    unittest.main()
