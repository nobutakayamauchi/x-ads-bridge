from __future__ import annotations

import unittest

from site_visits_campaign_factory import CampaignFactoryError, build_paused_site_visits_plan


class SiteVisitsCampaignFactoryTests(unittest.TestCase):
    def _plan(self):
        return build_paused_site_visits_plan(
            campaign_name="WAB_20260828_LPV_BASELINE",
            line_item_name="WAB_B2_SITE_VISITS_CURRENT_TARGET",
            funding_instrument_id="1b8nfk",
            start_time="2026-08-28T01:00:00Z",
            end_time="2026-08-31T07:00:00Z",
            daily_budget_jpy=1700,
            total_budget_jpy=2500,
            tweet_ids=["123456789"],
            targeting=[
                {"targeting_type": "LOCATION", "targeting_value": "06ef846bfc783874", "operator_type": "EQ"},
                {"targeting_type": "BROAD_KEYWORD", "targeting_value": "GPTs", "operator_type": "EQ"},
            ],
        )

    def test_plan_is_paused_and_changes_only_optimization_goal(self):
        plan = self._plan()
        self.assertEqual(plan["mode"], "PREPARE_PAUSED_ONLY")
        self.assertFalse(plan["activation_allowed"])
        self.assertEqual(plan["campaign"]["entity_status"], "PAUSED")
        self.assertEqual(plan["campaign"]["budget_optimization"], "LINE_ITEM")
        self.assertEqual(plan["line_item"]["entity_status"], "PAUSED")
        self.assertEqual(plan["line_item"]["objective"], "WEBSITE_CLICKS")
        self.assertEqual(plan["line_item"]["goal"], "SITE_VISITS")
        self.assertEqual(plan["line_item"]["bid_strategy"], "AUTO")
        self.assertEqual(plan["line_item"]["pay_by"], "IMPRESSION")
        self.assertNotIn("primary_web_event_tag", plan["line_item"])

    def test_budget_is_bounded_in_micro_currency(self):
        plan = self._plan()
        self.assertEqual(plan["line_item"]["daily_budget_amount_local_micro"], 1_700_000_000)
        self.assertEqual(plan["line_item"]["total_budget_amount_local_micro"], 2_500_000_000)

    def test_rejects_total_budget_below_daily_budget(self):
        with self.assertRaises(CampaignFactoryError):
            build_paused_site_visits_plan(
                campaign_name="x",
                line_item_name="y",
                funding_instrument_id="fi",
                start_time="2026-08-28T01:00:00Z",
                end_time="2026-08-31T07:00:00Z",
                daily_budget_jpy=1700,
                total_budget_jpy=1000,
                tweet_ids=["1"],
                targeting=[{"targeting_type": "BROAD_KEYWORD", "targeting_value": "GPTs"}],
            )


if __name__ == "__main__":
    unittest.main()
