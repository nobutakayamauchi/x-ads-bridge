from __future__ import annotations

import unittest

from experiment_benchmarks import evaluate_webai_lpv_run


class ExperimentBenchmarkTests(unittest.TestCase):
    def test_healthy_lpv_ratio_passes_directional_floor(self):
        result = evaluate_webai_lpv_run(
            {
                "spend_jpy": 1000,
                "impressions": 10000,
                "link_clicks": 40,
                "landing_page_views": 34,
                "consult_clicks": 2,
            },
            control={"cpc_jpy": 34.9, "cpm_jpy": 149, "click_to_lpv_pct": None},
        )
        self.assertEqual(result["metrics"]["click_to_lpv_pct"], 85.0)
        self.assertEqual(result["observations"][0]["state"], "PASS")
        self.assertEqual(result["hypothesis_state"], "LPV_SIGNAL_HEALTHY_PROCEED_TO_DOWNSTREAM_EVALUATION")
        self.assertFalse(result["scale_authority"])

    def test_low_lpv_ratio_requests_diagnosis(self):
        result = evaluate_webai_lpv_run(
            {
                "spend_jpy": 1000,
                "impressions": 10000,
                "link_clicks": 40,
                "landing_page_views": 20,
            }
        )
        self.assertEqual(result["metrics"]["click_to_lpv_pct"], 50.0)
        self.assertEqual(result["observations"][0]["state"], "DIAGNOSE")
        self.assertEqual(result["hypothesis_state"], "LPV_SIGNAL_WORKS_BUT_FUNNEL_GAP_REMAINS")

    def test_under_20_lpv_is_not_called_resolved(self):
        result = evaluate_webai_lpv_run(
            {
                "spend_jpy": 500,
                "impressions": 5000,
                "link_clicks": 15,
                "landing_page_views": 14,
            }
        )
        self.assertEqual(result["hypothesis_state"], "INSUFFICIENT_SAMPLE")

    def test_near_case_costs_are_context_not_authority(self):
        result = evaluate_webai_lpv_run(
            {
                "spend_jpy": 1200,
                "impressions": 8000,
                "link_clicks": 24,
                "landing_page_views": 22,
            }
        )
        self.assertGreater(result["cost_context"]["cpc_vs_recent_near_case_multiple"], 1)
        self.assertIn("not pass/fail", result["cost_context"]["warning"])
        self.assertFalse(result["scale_authority"])


if __name__ == "__main__":
    unittest.main()
