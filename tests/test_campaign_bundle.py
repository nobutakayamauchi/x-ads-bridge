from __future__ import annotations

import unittest

from campaign_bundle import (
    activate_campaign_bundle,
    create_paused_website_traffic_bundle,
    normalized_creation_plan,
)


BASE_COMMAND = {
    "funding_instrument_id": "fi1",
    "campaign_name": "Beta Campaign",
    "line_item_name": "Beta Ad Group",
    "start_time": "2026-08-28T03:00:00Z",
    "end_time": "2026-08-29T03:00:00Z",
    "daily_budget_jpy": 1000,
    "total_budget_jpy": 2000,
    "goal": "SITE_VISITS",
    "tweet_ids": ["123456"],
    "targeting": [
        {
            "targeting_type": "BROAD_KEYWORD",
            "targeting_value": "生成AI",
            "operator_type": "EQ",
        }
    ],
}


class CampaignBundleTests(unittest.TestCase):
    def test_normalized_plan_is_paused_shape_input(self):
        plan = normalized_creation_plan(BASE_COMMAND)
        self.assertEqual(plan["goal"], "SITE_VISITS")
        self.assertEqual(plan["tweet_ids"], ["123456"])
        self.assertEqual(len(plan["targeting"]), 1)

    def test_create_bundle_stays_paused_and_reads_back(self):
        calls = []

        def request(method, path, **kwargs):
            calls.append((method, path, kwargs))
            if method == "POST" and path.endswith("/campaigns"):
                self.assertEqual(kwargs["data"]["entity_status"], "PAUSED")
                return {"data": {"id": "camp1"}}
            if method == "POST" and path.endswith("/line_items"):
                self.assertEqual(kwargs["data"]["campaign_id"], "camp1")
                self.assertEqual(kwargs["data"]["entity_status"], "PAUSED")
                self.assertEqual(kwargs["data"]["objective"], "WEBSITE_CLICKS")
                self.assertEqual(kwargs["data"]["goal"], "SITE_VISITS")
                return {"data": {"id": "li1"}}
            if method == "POST" and path.endswith("/targeting_criteria"):
                return {"data": {"id": "tc1"}}
            if method == "POST" and path.endswith("/promoted_tweets"):
                return {"data": [{"id": "pt1", "tweet_id": "123456"}]}
            if method == "GET" and path.endswith("/campaigns/camp1"):
                return {"data": {"id": "camp1", "entity_status": "PAUSED"}}
            if method == "GET" and path.endswith("/line_items/li1"):
                return {
                    "data": {
                        "id": "li1",
                        "campaign_id": "camp1",
                        "entity_status": "PAUSED",
                    }
                }
            if method == "GET" and path.endswith("/targeting_criteria"):
                return {"data": [{"id": "tc1"}]}
            if method == "GET" and path.endswith("/promoted_tweets"):
                return {"data": [{"id": "pt1"}]}
            raise AssertionError((method, path, kwargs))

        result = create_paused_website_traffic_bundle(
            account_id="acc1", command=BASE_COMMAND, request_fn=request
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["delivery_started"])
        self.assertEqual(result["created"]["campaign_id"], "camp1")
        self.assertEqual(result["created"]["line_item_id"], "li1")
        self.assertGreaterEqual(len(calls), 8)

    def test_creation_partial_failure_reports_created_ids_without_rollback(self):
        def request(method, path, **kwargs):
            if method == "POST" and path.endswith("/campaigns"):
                return {"data": {"id": "camp1"}}
            if method == "POST" and path.endswith("/line_items"):
                return {"data": {"id": "li1"}}
            if method == "POST" and path.endswith("/targeting_criteria"):
                raise RuntimeError("targeting rejected")
            raise AssertionError((method, path))

        result = create_paused_website_traffic_bundle(
            account_id="acc1", command=BASE_COMMAND, request_fn=request
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["write_executed"])
        self.assertFalse(result["rollback_performed"])
        self.assertEqual(result["created"]["campaign_id"], "camp1")
        self.assertEqual(result["created"]["line_item_id"], "li1")

    def test_activation_requires_paused_bundle_and_reads_back_active(self):
        state = {"campaign": "PAUSED", "line": "PAUSED"}

        def request(method, path, **kwargs):
            if method == "GET" and path.endswith("/campaigns/camp1"):
                return {"data": {"id": "camp1", "entity_status": state["campaign"]}}
            if method == "GET" and path.endswith("/line_items/li1"):
                return {
                    "data": {
                        "id": "li1",
                        "campaign_id": "camp1",
                        "entity_status": state["line"],
                    }
                }
            if method == "PUT" and path.endswith("/campaigns/camp1"):
                state["campaign"] = "ACTIVE"
                return {"data": {"id": "camp1", "entity_status": "ACTIVE"}}
            if method == "PUT" and path.endswith("/line_items/li1"):
                state["line"] = "ACTIVE"
                return {"data": {"id": "li1", "entity_status": "ACTIVE"}}
            raise AssertionError((method, path))

        result = activate_campaign_bundle(
            account_id="acc1",
            command={"campaign_id": "camp1", "line_item_id": "li1"},
            request_fn=request,
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["delivery_may_start"])
        self.assertEqual(result["mode"], "BUNDLE_ACTIVE")

    def test_activation_second_write_failure_leaves_line_paused(self):
        state = {"campaign": "PAUSED", "line": "PAUSED"}

        def request(method, path, **kwargs):
            if method == "GET" and path.endswith("/campaigns/camp1"):
                return {"data": {"id": "camp1", "entity_status": state["campaign"]}}
            if method == "GET" and path.endswith("/line_items/li1"):
                return {
                    "data": {
                        "id": "li1",
                        "campaign_id": "camp1",
                        "entity_status": state["line"],
                    }
                }
            if method == "PUT" and path.endswith("/campaigns/camp1"):
                state["campaign"] = "ACTIVE"
                return {"data": {"id": "camp1", "entity_status": "ACTIVE"}}
            if method == "PUT" and path.endswith("/line_items/li1"):
                raise RuntimeError("line resume failed")
            raise AssertionError((method, path))

        result = activate_campaign_bundle(
            account_id="acc1",
            command={"campaign_id": "camp1", "line_item_id": "li1"},
            request_fn=request,
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["campaign_resumed"])
        self.assertFalse(result["line_item_resumed"])
        self.assertEqual(state["line"], "PAUSED")


if __name__ == "__main__":
    unittest.main()
