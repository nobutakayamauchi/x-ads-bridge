from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import operation_protocol as op


ACCOUNT_ID = "18ce55ut499"
BASE_ENV = {
    "XADS_ACCESS_TOKEN_SECRET": "unit-test-signing-secret",
    "XADS_ACCOUNT_ID": ACCOUNT_ID,
    "XADS_ALLOW_WRITES": "false",
    "XADS_MAX_DAILY_BUDGET_LOCAL": "2000",
    "XADS_EVENT_ACTION": "opened",
}


class OperationProtocol01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, BASE_ENV, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.proposed = {
            "action": "pause_line_item",
            "account_id": ACCOUNT_ID,
            "line_item_id": "line-item-1",
        }

    def _proposal(self) -> dict:
        return op.execute({"action": "prepare_proposal", "proposed_command": self.proposed})

    def _approval(self, proposal: dict) -> dict:
        return op.execute({
            "action": "issue_approval_hash",
            "approval_request_text": op.APPROVAL_HASH_REQUEST,
            "da_counter_da_review_complete": True,
            "proposed_command": self.proposed,
            "proposal_token": proposal["proposal_token"],
            "proposal_expires_at": proposal["proposal_expires_at"],
        })

    def _confirmed(self, proposal: dict, approval: dict) -> dict:
        return op.execute({
            "action": "confirm_approval",
            "proposed_command": self.proposed,
            "proposal_token": proposal["proposal_token"],
            "proposal_expires_at": proposal["proposal_expires_at"],
            "approval_token": approval["approval_token"],
            "approval_expires_at": approval["approval_expires_at"],
            "approval_text": approval["approval_text_required"],
        })

    def test_approval_and_execution_are_separate_non_write_stages(self):
        with patch.object(op.bridge, "_request") as request:
            proposal = self._proposal()
            approval = self._approval(proposal)
            confirmed = self._confirmed(proposal, approval)
        request.assert_not_called()
        self.assertFalse(proposal["write_executed"])
        self.assertFalse(approval["write_executed"])
        self.assertFalse(confirmed["write_executed"])
        self.assertTrue(approval["approval_hash"].startswith("XADS-"))
        self.assertTrue(confirmed["execution_key"].startswith("RUN-"))
        self.assertEqual(confirmed["status"], "APPROVED_NOT_RUNNING")

    def test_wrong_approval_hash_sentence_blocks(self):
        proposal = self._proposal()
        approval = self._approval(proposal)
        with self.assertRaisesRegex(op.OperationProtocolError, "approval text mismatch"):
            op.execute({
                "action": "confirm_approval",
                "proposed_command": self.proposed,
                "proposal_token": proposal["proposal_token"],
                "proposal_expires_at": proposal["proposal_expires_at"],
                "approval_token": approval["approval_token"],
                "approval_expires_at": approval["approval_expires_at"],
                "approval_text": approval["approval_hash"] + " 承認",
            })

    def test_changed_command_invalidates_approval(self):
        proposal = self._proposal()
        approval = self._approval(proposal)
        changed = {**self.proposed, "line_item_id": "line-item-2"}
        with self.assertRaisesRegex(op.OperationProtocolError, "proposal token"):
            op.execute({
                "action": "confirm_approval",
                "proposed_command": changed,
                "proposal_token": proposal["proposal_token"],
                "proposal_expires_at": proposal["proposal_expires_at"],
                "approval_token": approval["approval_token"],
                "approval_expires_at": approval["approval_expires_at"],
                "approval_text": approval["approval_text_required"],
            })

    def test_wrong_execution_key_sentence_blocks(self):
        proposal = self._proposal()
        approval = self._approval(proposal)
        confirmed = self._confirmed(proposal, approval)
        with patch.dict(os.environ, {"XADS_ALLOW_WRITES": "true"}, clear=False):
            with self.assertRaisesRegex(op.OperationProtocolError, "execution text mismatch"):
                op.execute({
                    "action": "execute_approved_operation",
                    "proposed_command": self.proposed,
                    "proposal_token": proposal["proposal_token"],
                    "proposal_expires_at": proposal["proposal_expires_at"],
                    "approval_token": approval["approval_token"],
                    "approval_expires_at": approval["approval_expires_at"],
                    "execution_token": confirmed["execution_token"],
                    "execution_expires_at": confirmed["execution_expires_at"],
                    "execution_text": confirmed["execution_key"] + " 実行",
                })

    def test_exact_execution_key_reaches_write_only_at_final_stage(self):
        proposal = self._proposal()
        approval = self._approval(proposal)
        confirmed = self._confirmed(proposal, approval)
        with patch.dict(os.environ, {"XADS_ALLOW_WRITES": "true"}, clear=False):
            with patch.object(op.bridge, "_request", return_value={"ok": True}) as request:
                result = op.execute({
                    "action": "execute_approved_operation",
                    "proposed_command": self.proposed,
                    "proposal_token": proposal["proposal_token"],
                    "proposal_expires_at": proposal["proposal_expires_at"],
                    "approval_token": approval["approval_token"],
                    "approval_expires_at": approval["approval_expires_at"],
                    "execution_token": confirmed["execution_token"],
                    "execution_expires_at": confirmed["execution_expires_at"],
                    "execution_text": confirmed["execution_text_required"],
                })
        self.assertTrue(result["write_executed"])
        request.assert_called_once_with(
            "PUT",
            f"accounts/{ACCOUNT_ID}/line_items/line-item-1",
            data={"entity_status": "PAUSED"},
        )


if __name__ == "__main__":
    unittest.main()
