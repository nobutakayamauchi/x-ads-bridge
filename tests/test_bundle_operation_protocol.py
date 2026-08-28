from __future__ import annotations

import unittest
from unittest.mock import patch

import bundle_operation_protocol as bop


PROPOSED_CREATE = {
    "action": "create_website_traffic_bundle_paused",
    "account_id": "acc1",
    "funding_instrument_id": "fi1",
    "campaign_name": "Beta Campaign",
    "line_item_name": "Beta Group",
    "start_time": "2026-08-28T03:00:00Z",
    "end_time": "2026-08-29T03:00:00Z",
    "daily_budget_jpy": 1000,
    "total_budget_jpy": 2000,
    "goal": "SITE_VISITS",
    "conversion_tag_id": "tag1",
    "tweet_ids": ["123456"],
    "targeting": [
        {
            "targeting_type": "BROAD_KEYWORD",
            "targeting_value": "生成AI",
            "operator_type": "EQ",
        }
    ],
}


ENV = {
    "XADS_ACCESS_TOKEN_SECRET": "test-signing-secret",
    "XADS_ACCOUNT_ID": "acc1",
    "XADS_ALLOW_WRITES": "true",
    "XADS_MAX_DAILY_BUDGET_LOCAL": "2000",
    "XADS_MAX_TOTAL_BUDGET_LOCAL": "5000",
    "XADS_EVENT_ACTION": "opened",
}


class BundleOperationProtocolTests(unittest.TestCase):
    def _issue_chain(self):
        proposal = bop.execute(
            {"action": "prepare_bundle_proposal", "proposed_command": PROPOSED_CREATE}
        )
        approval = bop.execute(
            {
                "action": "issue_bundle_approval_hash",
                "proposed_command": PROPOSED_CREATE,
                "proposal_token": proposal["proposal_token"],
                "proposal_expires_at": proposal["proposal_expires_at"],
                "approval_request_text": bop.APPROVAL_HASH_REQUEST,
                "da_counter_da_review_complete": True,
            }
        )
        confirmed = bop.execute(
            {
                "action": "confirm_bundle_approval",
                "proposed_command": PROPOSED_CREATE,
                "proposal_token": proposal["proposal_token"],
                "proposal_expires_at": proposal["proposal_expires_at"],
                "approval_token": approval["approval_token"],
                "approval_expires_at": approval["approval_expires_at"],
                "approval_text": approval["approval_text_required"],
            }
        )
        return proposal, approval, confirmed

    @patch.dict("os.environ", ENV, clear=False)
    def test_no_x_write_before_exact_execution_key(self):
        with patch("bridge._request") as request:
            proposal, approval, confirmed = self._issue_chain()
            self.assertFalse(proposal["write_executed"])
            self.assertFalse(approval["write_executed"])
            self.assertFalse(confirmed["write_executed"])
            request.assert_not_called()

    @patch.dict("os.environ", ENV, clear=False)
    def test_wrong_execution_text_blocks_before_write(self):
        proposal, approval, confirmed = self._issue_chain()
        with patch("bridge._request") as request:
            with self.assertRaises(bop.BundleOperationError):
                bop.execute(
                    {
                        "action": "execute_approved_bundle",
                        "proposed_command": PROPOSED_CREATE,
                        "proposal_token": proposal["proposal_token"],
                        "proposal_expires_at": proposal["proposal_expires_at"],
                        "approval_token": approval["approval_token"],
                        "approval_expires_at": approval["approval_expires_at"],
                        "execution_token": confirmed["execution_token"],
                        "execution_expires_at": confirmed["execution_expires_at"],
                        "execution_text": "実行",
                    }
                )
            request.assert_not_called()

    @patch.dict("os.environ", ENV, clear=False)
    def test_exact_execution_reaches_paused_creation_only(self):
        proposal, approval, confirmed = self._issue_chain()
        calls = []

        def request(method, path, **kwargs):
            calls.append((method, path, kwargs))
            if method == "POST" and path.endswith("/campaigns"):
                self.assertEqual(kwargs["data"]["entity_status"], "PAUSED")
                return {"data": {"id": "camp1"}}
            if method == "POST" and path.endswith("/line_items"):
                self.assertEqual(kwargs["data"]["entity_status"], "PAUSED")
                self.assertEqual(kwargs["data"]["conversion_tag_id"], "tag1")
                return {"data": {"id": "li1"}}
            if method == "POST" and path.endswith("/targeting_criteria"):
                return {"data": {"id": "tc1"}}
            if method == "POST" and path.endswith("/promoted_tweets"):
                return {"data": [{"id": "pt1"}]}
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

        with patch("bridge._request", side_effect=request):
            result = bop.execute(
                {
                    "action": "execute_approved_bundle",
                    "proposed_command": PROPOSED_CREATE,
                    "proposal_token": proposal["proposal_token"],
                    "proposal_expires_at": proposal["proposal_expires_at"],
                    "approval_token": approval["approval_token"],
                    "approval_expires_at": approval["approval_expires_at"],
                    "execution_token": confirmed["execution_token"],
                    "execution_expires_at": confirmed["execution_expires_at"],
                    "execution_text": confirmed["execution_text_required"],
                }
            )
        self.assertTrue(result["ok"])
        self.assertTrue(result["write_executed"])
        self.assertFalse(result["result"]["delivery_started"])
        self.assertTrue(any(method == "POST" for method, _, _ in calls))

    @patch.dict(
        "os.environ",
        {**ENV, "XADS_MAX_TOTAL_BUDGET_LOCAL": "1500"},
        clear=False,
    )
    def test_total_budget_cap_blocks_at_proposal_time(self):
        with self.assertRaises(bop.BundleOperationError):
            bop.execute(
                {"action": "prepare_bundle_proposal", "proposed_command": PROPOSED_CREATE}
            )


if __name__ == "__main__":
    unittest.main()
