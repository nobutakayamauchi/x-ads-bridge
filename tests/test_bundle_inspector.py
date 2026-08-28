from __future__ import annotations

import unittest
from unittest.mock import patch

import bundle_inspector


class BundleInspectorTests(unittest.TestCase):
    def test_inspects_line_item_without_writes(self):
        responses = [
            {"data": {"id": "line-1", "campaign_id": "camp-1"}},
            {"data": {"id": "camp-1", "funding_instrument_id": "fund-1"}},
            {"data": [{"id": "target-1", "targeting_type": "LOCATION", "targeting_value": "jp"}]},
            {"data": [{"id": "promoted-1", "tweet_id": "123"}]},
        ]
        with patch.object(bundle_inspector.bridge, "_request", side_effect=responses) as request:
            result = bundle_inspector.inspect_line_item_bundle(
                {"account_id": "acct-1", "line_item_id": "line-1"}
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["read_only"])
        self.assertFalse(result["write_executed"])
        self.assertEqual(result["campaign_id"], "camp-1")
        self.assertEqual(request.call_count, 4)
        for call in request.call_args_list:
            self.assertEqual(call.args[0], "GET")


if __name__ == "__main__":
    unittest.main()
