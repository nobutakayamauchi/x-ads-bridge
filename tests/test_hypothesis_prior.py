from __future__ import annotations

import unittest

from hypothesis_prior import build_directional_prior


class HypothesisPriorTests(unittest.TestCase):
    def test_correlated_official_cases_cannot_become_strong_support(self):
        cases = [
            {
                "case_id": "a",
                "source_kind": "official_x_case",
                "h1_evidence_class": "DIRECT",
                "direction": "SUPPORTS_H1",
                "verification": {"evidence_strength": 0.9, "bias_flags": []},
                "product_fit": {"score": 0.9},
            },
            {
                "case_id": "b",
                "source_kind": "official_x_product_test",
                "h1_evidence_class": "DIRECT",
                "direction": "SUPPORTS_H1",
                "verification": {"evidence_strength": 0.9, "bias_flags": []},
                "product_fit": {"score": 0.8},
            },
        ]
        prior = build_directional_prior(cases)
        self.assertEqual(prior["independent_source_families"], 1)
        self.assertEqual(prior["prior_class"], "MODERATE_DIRECTIONAL_SUPPORT_INDEPENDENCE_LIMITED")
        self.assertFalse(prior["scale_authority"])

    def test_independent_direct_support_can_be_strong(self):
        cases = [
            {
                "case_id": "official",
                "source_kind": "official_x_case",
                "h1_evidence_class": "DIRECT",
                "direction": "SUPPORTS_H1",
                "verification": {"evidence_strength": 0.9, "bias_flags": []},
                "product_fit": {"score": 0.9},
            },
            {
                "case_id": "operator",
                "source_kind": "x_recent_search",
                "h1_evidence_class": "DIRECT",
                "direction": "SUPPORTS_H1",
                "verification": {"evidence_strength": 0.75, "bias_flags": []},
                "product_fit": {"score": 0.85},
            },
        ]
        prior = build_directional_prior(cases)
        self.assertEqual(prior["independent_source_families"], 2)
        self.assertEqual(prior["prior_class"], "STRONG_DIRECTIONAL_SUPPORT")

    def test_refuting_case_reduces_directional_score(self):
        supporting_only = [
            {
                "case_id": "support",
                "source_kind": "official_x_case",
                "h1_evidence_class": "DIRECT",
                "direction": "SUPPORTS_H1",
                "verification": {"evidence_strength": 1.0, "bias_flags": []},
                "product_fit": {"score": 1.0},
            }
        ]
        mixed = supporting_only + [
            {
                "case_id": "refute",
                "source_kind": "x_recent_search",
                "h1_evidence_class": "DIRECT",
                "direction": "REFUTES_H1",
                "verification": {"evidence_strength": 1.0, "bias_flags": []},
                "product_fit": {"score": 1.0},
            }
        ]
        self.assertGreater(
            build_directional_prior(supporting_only)["directional_score"],
            build_directional_prior(mixed)["directional_score"],
        )


if __name__ == "__main__":
    unittest.main()
