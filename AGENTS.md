# AGENTS.md

## Repository role
x-ads-bridge is an evidence-first campaign/ads bridge that prepares campaign bundles, evaluates objective/sellability/authority boundaries, and stops at human-reviewed execution unless explicitly approved otherwise.

## Canonical load order
1. Read `README.md`.
2. Read `APPROVAL_PROTOCOL.md` for authority/Human Gate.
3. Load only the protocol applicable to the current question: `CASE_EVIDENCE_PROTOCOL.md`, `OBJECTIVE_AUDIT_PROTOCOL.md`, `SELLABILITY_GATE.md`, `STRIPE_AUTHORITY_JOIN.md`, or `EVOLUTION_PROTOCOL.md`.
4. Read the exact implementation module/tests needed for the active bundle or bridge operation.
5. Load historical/generated bundles only when validating a specific case/run.

## Source of truth
- Explicit evidence and authority protocols outrank generated campaign copy.
- Case evidence must remain separate from hypotheses and outcome claims.
- Payment/Stripe evidence does not create advertising/account authority.
- A generated bundle is preparation, not approval or publication.

## Context budget
- Do not load every root protocol before each task.
- Start from the active objective and load the narrowest applicable gate.
- Work one case/campaign bundle at a time where possible.
- Do not load all generated outputs/history unless comparison or diagnosis requires it.

## Human gates
Ad publication, spend/budget changes, account mutation, external messaging, payment actions, production changes, deletion, or permission changes require explicit human approval.

## Stop conditions
Stop on missing campaign authority, ambiguous payment/account ownership, unsupported outcome claims, evidence conflict, or any requested action that bypasses the applicable approval protocol.