from __future__ import annotations

import unittest

from objective_audit import audit_campaign


class ObjectiveAuditTests(unittest.TestCase):
    def test_missing_contract_never_scales(self):
        result = audit_campaign(None, {"x_link_clicks": 100, "spend_jpy": 1000})
        self.assertEqual(result["state"], "INSUFFICIENT_EVIDENCE")
        self.assertFalse(result["scale_allowed"])

    def test_cheap_clicks_without_purchase_do_not_scale(self):
        contract = {
            "primary_objective": "purchase",
            "target_count": 1,
            "max_spend_jpy": 5000,
            "evaluation_window": "campaign-test",
            "diagnosis_min_x_clicks": 50,
        }
        evidence = {
            "x_link_clicks": 100,
            "lp_unique": 80,
            "purchase_click_unique": 0,
            "stripe_paid_purchases": 0,
            "spend_jpy": 2000,
        }
        result = audit_campaign(contract, evidence)
        self.assertEqual(result["state"], "DIAGNOSE")
        self.assertFalse(result["scale_allowed"])

    def test_max_spend_without_objective_is_stop(self):
        contract = {
            "primary_objective": "purchase",
            "target_count": 1,
            "max_spend_jpy": 5000,
            "evaluation_window": "campaign-test",
        }
        result = audit_campaign(
            contract,
            {
                "x_link_clicks": 200,
                "lp_unique": 150,
                "purchase_click_unique": 10,
                "stripe_paid_purchases": 0,
                "spend_jpy": 5000,
            },
        )
        self.assertEqual(result["state"], "STOP")
        self.assertFalse(result["scale_allowed"])

    def test_purchase_target_inside_boundary_can_scale(self):
        contract = {
            "primary_objective": "purchase",
            "target_count": 2,
            "max_spend_jpy": 5000,
            "evaluation_window": "campaign-test",
            "target_cpa_jpy": 2000,
        }
        result = audit_campaign(
            contract,
            {
                "x_link_clicks": 100,
                "lp_unique": 70,
                "purchase_click_unique": 5,
                "stripe_paid_purchases": 2,
                "spend_jpy": 3000,
            },
        )
        self.assertEqual(result["state"], "SCALE")
        self.assertTrue(result["scale_allowed"])
        self.assertEqual(result["actual_cpa_jpy"], 1500)

    def test_purchase_target_with_bad_cpa_holds(self):
        contract = {
            "primary_objective": "purchase",
            "target_count": 1,
            "max_spend_jpy": 5000,
            "evaluation_window": "campaign-test",
            "target_cpa_jpy": 1000,
        }
        result = audit_campaign(
            contract,
            {
                "stripe_paid_purchases": 1,
                "spend_jpy": 2500,
            },
        )
        self.assertEqual(result["state"], "HOLD")
        self.assertFalse(result["scale_allowed"])


if __name__ == "__main__":
    unittest.main()
