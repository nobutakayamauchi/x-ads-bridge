# x-ads-bridge

Evidence-first campaign/ads bridge for preparing bounded campaign bundles, objective checks, authority checks, and human-reviewed execution packets.

## Repository role

This repository combines campaign preparation logic with explicit approval, evidence, sellability, objective-audit, and payment/authority boundaries.

It is not a license to publish ads, spend money, mutate ad accounts, or treat generated campaign material as approved merely because a bundle was produced.

## Start here

1. `AGENTS.md` — AI operating boundary and context budget.
2. `APPROVAL_PROTOCOL.md` — authority and Human Gate.
3. `CASE_EVIDENCE_PROTOCOL.md` — evidence rules when case claims are involved.
4. Load `OBJECTIVE_AUDIT_PROTOCOL.md`, `SELLABILITY_GATE.md`, `STRIPE_AUTHORITY_JOIN.md`, or `EVOLUTION_PROTOCOL.md` only when that specific gate is material.
5. Load the exact Python module/tests needed for the active operation.

## Core rule

```text
BUNDLE CREATED != CAMPAIGN APPROVED
PAYMENT/STRIPE EVIDENCE != AD AUTHORITY
OBSERVED CASE != GUARANTEED OUTCOME
AI PROPOSAL != EXTERNAL MUTATION AUTHORITY
```

## Context rule

Do not ingest every protocol and every bundle/output by default. Start from the active objective, then load only the applicable gate plus the exact implementation/test path.