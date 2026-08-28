from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


REQUIRED_FILES = (
    "SELLABILITY_GATE.md",
    "skills/x-ads-daseru-kun/SKILL.md",
    "skills/x-ads-daseru-kun/references/OPERATION_PROTOCOL_01.md",
    "campaign_bundle.py",
    "bundle_operation_protocol.py",
    "bundle_issue_runner.py",
    ".github/workflows/xads-bundle-operation.yml",
    "reporting_dashboard.py",
    "docs/X_INTEGRATION_REVIEW_PACKET.md",
    "docs/X_REVIEW_SUBMISSION_MESSAGE.md",
    "docs/X_APPROVAL_ACTION.md",
    "docs/CUSTOMER_ONBOARDING.md",
    "docs/OFFBOARDING.md",
    "docs/PRICING_AND_BILLING.md",
    "docs/PRIVACY_SECURITY_BASELINE.md",
    "docs/REPORTING_REQUIREMENTS.md",
    "docs/CREATION_BETA_CONTRACT.md",
    "docs/SELLABLE_BETA_SCOPE.md",
    "docs/PRE_SALE_CHECKLIST.md",
)


@dataclass(frozen=True)
class Gate:
    name: str
    passed: bool
    detail: str


def _env_true(name: str) -> bool:
    return os.getenv(name, "").strip().lower() == "true"


def evaluate(root: Path | None = None) -> dict[str, object]:
    root = root or Path(__file__).resolve().parent
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]

    gates = [
        Gate(
            "technical_and_documentation_p0",
            not missing,
            "missing: " + ", ".join(missing) if missing else "ok",
        ),
        Gate(
            "x_integration_approved",
            _env_true("XADS_X_INTEGRATION_APPROVED"),
            "Set only after written X approval has been received and retained.",
        ),
        Gate(
            "external_e2e_acceptance_passed",
            _env_true("XADS_EXTERNAL_E2E_ACCEPTANCE_PASSED"),
            "Set only after a non-owner/customer-like dedicated deployment passes the full flow.",
        ),
    ]
    sellable = all(gate.passed for gate in gates)
    return {
        "sellable": sellable,
        "status": "GO" if sellable else "NO_GO",
        "gates": [asdict(gate) for gate in gates],
        "rule": "SELLABLE = TECHNICAL_P0 && X_INTEGRATION_APPROVED && EXTERNAL_E2E_ACCEPTANCE_PASSED",
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["sellable"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
