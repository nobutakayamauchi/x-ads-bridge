from __future__ import annotations

import unittest
from unittest.mock import patch

import reporting_dashboard as rd


QUERY = {
    "entity": ["LINE_ITEM"],
    "entity_ids": ["li1"],
    "start_time": ["2026-08-28T00:00:00Z"],
    "end_time": ["2026-08-28T01:00:00Z"],
    "granularity": ["TOTAL"],
    "placement": ["ALL_ON_TWITTER"],
}


class ReportingDashboardTests(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {
            "XADS_ACCOUNT_ID": "acc1",
            "XADS_SERVICE_FEE_PERCENT": "10",
            "XADS_REPORT_USERNAME": "client",
            "XADS_REPORT_PASSWORD": "strong-password",
        },
        clear=False,
    )
    def test_fetches_every_metric_group_and_marks_unavailable(self):
        calls = []

        def execute(command):
            calls.append(command["metric_groups"])
            if command["metric_groups"] == "MOBILE_CONVERSION":
                raise RuntimeError("not enabled")
            if command["metric_groups"] == "BILLING":
                return {"data": [{"id_data": [{"metrics": {"billed_charge_local_micro": [10000000]}}]}]}
            return {"data": []}

        with patch("reporting_dashboard.bridge.execute", side_effect=execute):
            report = rd.fetch_all_metric_groups(QUERY)

        self.assertEqual(set(calls), set(rd.METRIC_GROUPS))
        self.assertFalse(report["metric_groups"]["MOBILE_CONVERSION"]["available"])
        self.assertTrue(report["metric_groups"]["BILLING"]["available"])
        costs = rd.summarize_costs(report)
        self.assertEqual(costs["x_ads_spend_local"], 10.0)
        self.assertEqual(costs["company_service_fee_local"], 1.0)
        self.assertEqual(costs["combined_economic_cost_local"], 11.0)

    @patch.dict(
        "os.environ",
        {
            "XADS_REPORT_USERNAME": "client",
            "XADS_REPORT_PASSWORD": "pw",
        },
        clear=False,
    )
    def test_basic_auth_requires_exact_header(self):
        import base64

        token = base64.b64encode(b"client:pw").decode("ascii")
        self.assertTrue(rd._authorized(f"Basic {token}"))
        self.assertFalse(rd._authorized("Basic wrong"))
        self.assertFalse(rd._authorized(None))

    def test_request_validation_requires_entity_ids_and_times(self):
        with self.assertRaises(rd.ReportingError):
            rd._validate_request({"entity": ["LINE_ITEM"]})


if __name__ == "__main__":
    unittest.main()
