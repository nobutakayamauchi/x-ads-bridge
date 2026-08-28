from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sellability_audit as sa


class SellabilityAuditTests(unittest.TestCase):
    def _root_with_required_files(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for rel in sa.REQUIRED_FILES:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("ok", encoding="utf-8")
        return root

    def test_no_go_without_x_approval_and_external_e2e(self):
        root = self._root_with_required_files()
        with patch.dict(
            "os.environ",
            {
                "XADS_X_INTEGRATION_APPROVED": "false",
                "XADS_EXTERNAL_E2E_ACCEPTANCE_PASSED": "false",
            },
            clear=False,
        ):
            result = sa.evaluate(root)
        self.assertFalse(result["sellable"])
        self.assertEqual(result["status"], "NO_GO")

    def test_go_only_when_all_gates_are_true(self):
        root = self._root_with_required_files()
        with patch.dict(
            "os.environ",
            {
                "XADS_X_INTEGRATION_APPROVED": "true",
                "XADS_EXTERNAL_E2E_ACCEPTANCE_PASSED": "true",
            },
            clear=False,
        ):
            result = sa.evaluate(root)
        self.assertTrue(result["sellable"])
        self.assertEqual(result["status"], "GO")

    def test_missing_technical_file_blocks_even_with_external_gates(self):
        root = self._root_with_required_files()
        (root / "reporting_dashboard.py").unlink()
        with patch.dict(
            "os.environ",
            {
                "XADS_X_INTEGRATION_APPROVED": "true",
                "XADS_EXTERNAL_E2E_ACCEPTANCE_PASSED": "true",
            },
            clear=False,
        ):
            result = sa.evaluate(root)
        self.assertFalse(result["sellable"])
        self.assertIn("reporting_dashboard.py", str(result["gates"][0]["detail"]))


if __name__ == "__main__":
    unittest.main()
