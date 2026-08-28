from __future__ import annotations

import unittest
from datetime import datetime, timezone

from control_completion import evaluate_control_completion


NOW = datetime(2026, 8, 28, 1, 0, tzinfo=timezone.utc)


class ControlCompletionTests(unittest.TestCase):
    def _line_item(self, **overrides):
        item = {
            "entity_status": "ACTIVE",
            "effective_status": "RUNNING",
            "total_budget_amount_local_micro": 5_000_000_000,
            "end_time": "2026-08-28T07:00:00Z",
            "reasons_not_servable": [],
        }
        item.update(overrides)
        return item

    def test_running_control_below_budget_waits(self):
        result = evaluate_control_completion(
            self._line_item(),
            billed_charge_local_micro=4_607_206_686,
            now=NOW,
        )
        self.assertFalse(result["BUDGET_EXHAUSTED"])
        self.assertFalse(result["CONTROL_CLOSED"])
        self.assertFalse(result["READY_FOR_NEXT"])
        self.assertEqual(result["FLAG"], "WAIT")
        self.assertEqual(result["remaining_jpy"], 392.79)

    def test_budget_exhaustion_sets_ready(self):
        result = evaluate_control_completion(
            self._line_item(),
            billed_charge_local_micro=5_000_000_000,
            now=NOW,
        )
        self.assertTrue(result["BUDGET_EXHAUSTED"])
        self.assertTrue(result["CONTROL_CLOSED"])
        self.assertTrue(result["READY_FOR_NEXT"])
        self.assertEqual(result["FLAG"], "READY")

    def test_one_yen_tolerance_handles_budget_rounding(self):
        result = evaluate_control_completion(
            self._line_item(),
            billed_charge_local_micro=4_999_500_000,
            now=NOW,
        )
        self.assertTrue(result["BUDGET_EXHAUSTED"])
        self.assertEqual(result["remaining_jpy"], 0.5)

    def test_end_time_can_close_without_claiming_budget_exhausted(self):
        result = evaluate_control_completion(
            self._line_item(end_time="2026-08-28T00:00:00Z"),
            billed_charge_local_micro=4_900_000_000,
            now=NOW,
        )
        self.assertFalse(result["BUDGET_EXHAUSTED"])
        self.assertTrue(result["CONTROL_CLOSED"])
        self.assertTrue(result["READY_FOR_NEXT"])
        self.assertIn("END_TIME_REACHED", result["reason_codes"])

    def test_paused_is_not_treated_as_complete(self):
        result = evaluate_control_completion(
            self._line_item(entity_status="PAUSED", effective_status="PAUSED"),
            billed_charge_local_micro=4_000_000_000,
            now=NOW,
        )
        self.assertFalse(result["CONTROL_CLOSED"])
        self.assertEqual(result["FLAG"], "WAIT")

    def test_budget_not_servable_reason_closes_control(self):
        result = evaluate_control_completion(
            self._line_item(reasons_not_servable=["TOTAL_BUDGET_EXHAUSTED"]),
            billed_charge_local_micro=4_990_000_000,
            now=NOW,
        )
        self.assertFalse(result["BUDGET_EXHAUSTED"])
        self.assertTrue(result["CONTROL_CLOSED"])
        self.assertTrue(result["READY_FOR_NEXT"])
        self.assertIn("X_BUDGET_STOP_REASON", result["reason_codes"])


if __name__ == "__main__":
    unittest.main()
