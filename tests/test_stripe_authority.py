from __future__ import annotations

import unittest

from authority_audit import audit_with_stripe_authority
from stripe_authority import join_stripe_authority


STRIPE_CONTRACT = {
    "product_metadata_value": "webai_bridge",
    "purchase_payment_link": "plink_purchase",
    "purchase_amount_jpy": 98000,
    "purchase_purpose": "PUBLIC_SALES_LP",
    "consultation_payment_link": "plink_consult",
    "consultation_purpose": "PUBLIC_SALES_INQUIRY",
}


def purchase_session(*, ref: str | None, payment_link: str = "plink_purchase") -> dict:
    return {
        "id": "cs_live_purchase_1",
        "created": 100,
        "livemode": True,
        "status": "complete",
        "payment_status": "paid",
        "amount_total": 98000,
        "currency": "jpy",
        "payment_link": payment_link,
        "payment_intent": "pi_purchase_1",
        "client_reference_id": ref,
        "metadata": {
            "product": "webai_bridge",
            "purpose": "PUBLIC_SALES_LP",
        },
    }


class StripeAuthorityTests(unittest.TestCase):
    def test_exact_joined_paid_purchase_is_authoritative(self):
        result = join_stripe_authority(
            STRIPE_CONTRACT,
            [{"client_reference_id": "wab_session-1", "events": ["lp_view", "purchase_click"]}],
            [purchase_session(ref="wab_session-1")],
        )
        self.assertEqual(result["stripe_paid_purchases"], 1)
        self.assertEqual(result["unjoined_paid_purchase_candidates"], 0)

    def test_paid_but_unjoined_purchase_never_counts(self):
        result = join_stripe_authority(
            STRIPE_CONTRACT,
            [],
            [purchase_session(ref=None)],
        )
        self.assertEqual(result["stripe_paid_purchases"], 0)
        self.assertEqual(result["unjoined_paid_purchase_candidates"], 1)

    def test_wrong_payment_link_is_ignored(self):
        result = join_stripe_authority(
            STRIPE_CONTRACT,
            [{"client_reference_id": "wab_session-1", "events": ["purchase_click"]}],
            [purchase_session(ref="wab_session-1", payment_link="plink_other")],
        )
        self.assertEqual(result["stripe_paid_purchases"], 0)
        self.assertEqual(result["unjoined_paid_purchase_candidates"], 0)

    def test_joined_consultation_completion_is_authoritative(self):
        consultation = {
            "id": "cs_live_consult_1",
            "created": 100,
            "livemode": True,
            "status": "complete",
            "payment_status": "no_payment_required",
            "amount_total": 0,
            "currency": "jpy",
            "payment_link": "plink_consult",
            "payment_intent": None,
            "client_reference_id": "wab_session-2",
            "metadata": {
                "product": "webai_bridge",
                "purpose": "PUBLIC_SALES_INQUIRY",
            },
        }
        result = join_stripe_authority(
            STRIPE_CONTRACT,
            [{"client_reference_id": "wab_session-2", "events": ["consult_click"]}],
            [consultation],
        )
        self.assertEqual(result["stripe_consultation_completions"], 1)

    def test_unjoined_paid_session_cannot_unlock_scale(self):
        objective = {
            "primary_objective": "purchase",
            "target_count": 1,
            "max_spend_jpy": 5000,
            "evaluation_window": "reality-test",
            "diagnosis_min_x_clicks": 10,
        }
        report = audit_with_stripe_authority(
            objective_contract=objective,
            evidence={
                "x_link_clicks": 77,
                "lp_unique": 5,
                "purchase_click_unique": 1,
                "spend_jpy": 2924.62,
            },
            stripe_contract=STRIPE_CONTRACT,
            audited_join_keys=[],
            checkout_sessions=[purchase_session(ref=None)],
        )
        self.assertEqual(report["authority"]["stripe_paid_purchases"], 0)
        self.assertEqual(report["decision"]["state"], "DIAGNOSE")
        self.assertFalse(report["decision"]["scale_allowed"])


if __name__ == "__main__":
    unittest.main()
