from __future__ import annotations

import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from x_signal_collector import XSignalError, collection_plan, estimate_post_read_cost_usd, search_recent_posts


class XSignalCollectorTests(unittest.TestCase):
    def test_cost_estimate_for_default_bounded_sample(self):
        self.assertEqual(estimate_post_read_cost_usd(20), Decimal("0.100"))

    @patch.dict(os.environ, {}, clear=False)
    def test_collection_plan_is_blocked_by_default(self):
        os.environ.pop("X_SIGNAL_ALLOW_PAID_READS", None)
        os.environ.pop("X_SIGNAL_MAX_COST_USD_PER_RUN", None)
        plan = collection_plan("GPTs 販売 lang:ja -is:retweet", max_results=20)
        self.assertTrue(plan["within_cost_cap"])
        self.assertFalse(plan["paid_reads_enabled"])
        self.assertEqual(plan["estimated_max_cost_usd"], "0.100")

    @patch.dict(
        os.environ,
        {"X_SIGNAL_ALLOW_PAID_READS": "true", "X_SIGNAL_MAX_COST_USD_PER_RUN": "0.10"},
        clear=False,
    )
    def test_cost_cap_blocks_oversized_run(self):
        with self.assertRaisesRegex(XSignalError, "exceeds configured cap"):
            search_recent_posts("生成AI", max_results=100)

    def test_invalid_result_count_is_rejected(self):
        with self.assertRaises(XSignalError):
            estimate_post_read_cost_usd(101)


if __name__ == "__main__":
    unittest.main()
