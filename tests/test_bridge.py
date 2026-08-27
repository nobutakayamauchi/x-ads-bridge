from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import bridge


ACCOUNT_ID = "18ce55ut499"
BASE_ENV = {
    "XADS_ACCESS_TOKEN_SECRET": "unit-test-signing-secret",
    "XADS_ACCOUNT_ID": ACCOUNT_ID,
    "XADS_ALLOW_WRITES": "false",
    "XADS_MAX_DAILY_BUDGET_LOCAL": "2000",
    "XADS_EVENT_ACTION": "opened",
}


class ApprovalProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, BASE_ENV, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def _proposal(self, **overrides):
        command = {
            "action": "pause_line_item",
            "account_id": ACCOUNT_ID,
            "line_item_id": "line-item-1",
        }
        command.update(overrides)
        result = bridge.execute(command)
        self.assertEqual(result["mode"], "proposal")
        self.assertFalse(result["write_executed"])
        self.assertFalse(result["formal_approval_text_issued"])
        self.assertEqual(len(result["proposal_token"]), bridge.TOKEN_LENGTH)
        self.assertGreater(result["proposal_expires_at"], bridge._now_epoch())
        return command, result

    def _formal(self, proposed, proposal):
        result = bridge.execute(
            {
                "action": "issue_write_approval",
                "approval_request_text": bridge.FORMAL_APPROVAL_REQUEST,
                "da_counter_da_review_complete": True,
                "proposal_token": proposal["proposal_token"],
                "proposal_expires_at": proposal["proposal_expires_at"],
                "proposed_command": proposed,
            }
        )
        self.assertEqual(result["mode"], "formal_approval_issued")
        self.assertFalse(result["write_executed"])
        self.assertTrue(result["proposal_token_verified"])
        self.assertEqual(result["proposal_token"], proposal["proposal_token"])
        self.assertEqual(len(result["approval_token"]), bridge.TOKEN_LENGTH)
        self.assertGreater(result["approval_expires_at"], bridge._now_epoch())
        return result

    def _execution_command(self, proposed, proposal, formal):
        return {
            **proposed,
            "proposal_token": proposal["proposal_token"],
            "proposal_expires_at": proposal["proposal_expires_at"],
            "approval_token": formal["approval_token"],
            "approval_expires_at": formal["approval_expires_at"],
            "approval_text": formal["formal_approval_text"],
            "user_approved": True,
        }

    def test_proposal_tokens_are_randomized(self):
        _, first = self._proposal()
        _, second = self._proposal()
        self.assertNotEqual(first["proposal_token"], second["proposal_token"])

    def test_formal_approval_requires_exact_request_phrase(self):
        proposed, proposal = self._proposal()
        with self.assertRaisesRegex(bridge.BridgeError, "approval_request_text"):
            bridge.execute(
                {
                    "action": "issue_write_approval",
                    "approval_request_text": "正式承認文出して",
                    "da_counter_da_review_complete": True,
                    "proposal_token": proposal["proposal_token"],
                    "proposal_expires_at": proposal["proposal_expires_at"],
                    "proposed_command": proposed,
                }
            )

    def test_formal_approval_requires_da_counter_da_complete(self):
        proposed, proposal = self._proposal()
        with self.assertRaisesRegex(bridge.BridgeError, "DA/counter-DA"):
            bridge.execute(
                {
                    "action": "issue_write_approval",
                    "approval_request_text": bridge.FORMAL_APPROVAL_REQUEST,
                    "da_counter_da_review_complete": False,
                    "proposal_token": proposal["proposal_token"],
                    "proposal_expires_at": proposal["proposal_expires_at"],
                    "proposed_command": proposed,
                }
            )

    def test_expired_proposal_cannot_issue_formal_approval(self):
        proposed, proposal = self._proposal()
        future = proposal["proposal_expires_at"] + 1
        with patch.object(bridge, "_now_epoch", return_value=future):
            with self.assertRaisesRegex(bridge.BridgeError, "expired"):
                self._formal(proposed, proposal)

    def test_proposal_token_is_bound_to_exact_command(self):
        proposed, proposal = self._proposal()
        tampered = {**proposed, "line_item_id": "line-item-2"}
        with self.assertRaisesRegex(bridge.BridgeError, "proposal_token"):
            self._formal(tampered, proposal)

    def test_approval_token_is_bound_to_proposal_token(self):
        proposed, proposal_a = self._proposal()
        _, proposal_b = self._proposal()
        formal = self._formal(proposed, proposal_a)

        execution = {
            **proposed,
            "proposal_token": proposal_b["proposal_token"],
            "proposal_expires_at": proposal_b["proposal_expires_at"],
            "approval_token": formal["approval_token"],
            "approval_expires_at": formal["approval_expires_at"],
            "approval_text": formal["formal_approval_text"],
            "user_approved": True,
        }
        with self.assertRaisesRegex(bridge.BridgeError, "approval_token"):
            bridge.execute(execution)

    def test_expired_formal_approval_blocks_execution(self):
        proposed, proposal = self._proposal()
        formal = self._formal(proposed, proposal)
        execution = self._execution_command(proposed, proposal, formal)
        future = formal["approval_expires_at"] + 1

        with patch.object(bridge, "_now_epoch", return_value=future):
            with patch.dict(os.environ, {"XADS_ALLOW_WRITES": "true"}, clear=False):
                with self.assertRaisesRegex(bridge.BridgeError, "expired"):
                    bridge.execute(execution)

    def test_one_character_approval_text_difference_blocks(self):
        proposed, proposal = self._proposal()
        formal = self._formal(proposed, proposal)
        execution = self._execution_command(proposed, proposal, formal)
        execution["approval_text"] += "。"

        with self.assertRaisesRegex(bridge.BridgeError, "character-for-character"):
            bridge.execute(execution)

    def test_master_switch_blocks_valid_approval(self):
        proposed, proposal = self._proposal()
        formal = self._formal(proposed, proposal)
        execution = self._execution_command(proposed, proposal, formal)

        with self.assertRaisesRegex(bridge.BridgeError, "XADS_ALLOW_WRITES"):
            bridge.execute(execution)

    def test_reopened_issue_blocks_valid_approval(self):
        proposed, proposal = self._proposal()
        formal = self._formal(proposed, proposal)
        execution = self._execution_command(proposed, proposal, formal)

        with patch.dict(
            os.environ,
            {"XADS_ALLOW_WRITES": "true", "XADS_EVENT_ACTION": "reopened"},
            clear=False,
        ):
            with self.assertRaisesRegex(bridge.BridgeError, "newly opened issue"):
                bridge.execute(execution)

    def test_wrong_account_blocks_valid_approval(self):
        proposed, proposal = self._proposal(account_id="different-account")
        formal = self._formal(proposed, proposal)
        execution = self._execution_command(proposed, proposal, formal)

        with patch.dict(os.environ, {"XADS_ALLOW_WRITES": "true"}, clear=False):
            with self.assertRaisesRegex(bridge.BridgeError, "pinned XADS_ACCOUNT_ID"):
                bridge.execute(execution)

    def test_valid_opened_approval_can_reach_write_request(self):
        proposed, proposal = self._proposal()
        formal = self._formal(proposed, proposal)
        execution = self._execution_command(proposed, proposal, formal)

        with patch.dict(os.environ, {"XADS_ALLOW_WRITES": "true"}, clear=False):
            with patch.object(bridge, "_request", return_value={"ok": True}) as request:
                result = bridge.execute(execution)

        self.assertEqual(result, {"ok": True})
        request.assert_called_once_with(
            "PUT",
            f"accounts/{ACCOUNT_ID}/line_items/line-item-1",
            data={"entity_status": "PAUSED"},
        )

    def test_line_item_daily_budget_uses_same_approval_gate_and_cap(self):
        proposed = {
            "action": "set_line_item_daily_budget",
            "account_id": ACCOUNT_ID,
            "line_item_id": "line-item-1",
            "amount_local": 1700,
        }
        proposal = bridge.execute(proposed)
        formal = self._formal(proposed, proposal)
        execution = self._execution_command(proposed, proposal, formal)

        with patch.dict(os.environ, {"XADS_ALLOW_WRITES": "true"}, clear=False):
            with patch.object(bridge, "_request", return_value={"ok": True}) as request:
                bridge.execute(execution)

        request.assert_called_once_with(
            "PUT",
            f"accounts/{ACCOUNT_ID}/line_items/line-item-1",
            data={"daily_budget_amount_local_micro": 1700000000},
        )

    def test_budget_above_cap_blocks_after_valid_approval(self):
        proposed = {
            "action": "set_line_item_daily_budget",
            "account_id": ACCOUNT_ID,
            "line_item_id": "line-item-1",
            "amount_local": 2500,
        }
        proposal = bridge.execute(proposed)
        formal = self._formal(proposed, proposal)
        execution = self._execution_command(proposed, proposal, formal)

        with patch.dict(os.environ, {"XADS_ALLOW_WRITES": "true"}, clear=False):
            with self.assertRaisesRegex(bridge.BridgeError, "exceeds configured cap"):
                bridge.execute(execution)


if __name__ == "__main__":
    unittest.main()
