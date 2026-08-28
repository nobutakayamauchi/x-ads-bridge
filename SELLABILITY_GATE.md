# X Ads Bridge — Sellability Gate

Status: **PRE-LAUNCH / X APPROVAL REQUIRED**

This file is the single source of truth for whether the product may be sold to a third party.

## Launch rule

Do **not** commercialize, market, sell, or provide third-party access while any P0 item below is open.

## P0 — must be true before first paid customer

- [x] Conversational operation protocol exists (`skills/x-ads-daseru-kun/SKILL.md`).
- [x] Approval and execution are separate gates (`XADS-...` approval hash, then `RUN-...` execution key).
- [x] Legacy write route cannot perform paid writes; only current approval-gated routes may reach writes.
- [x] Account pinning, master write switch, daily/total budget breakers, exact approval, expiry, and new-issue execution guards remain enforced.
- [x] New website-traffic campaign bundle can be created PAUSED from confirmed existing X Post IDs.
- [x] PAUSED creation reads back campaign, line item, targeting, and promoted Post state.
- [x] Partial multi-step creation reports created IDs and never performs an automatic destructive rollback.
- [x] Bundle activation is a separate approval-hash/execution-key operation from bundle creation.
- [x] Activation requires campaign and line item to both be PAUSED immediately before execution.
- [x] Deployment model is one customer = one dedicated deployment/repository/secrets set.
- [x] Customer credentials are never requested in ChatGPT messages, GitHub Issues, comments, or logs.
- [x] Customer can disconnect by revoking the app from X Connected Apps and disabling/removing the dedicated deployment.
- [x] Authenticated customer-facing reporting offers every documented Ads API analytics metric group and surfaces unsupported groups as unavailable.
- [x] Pricing model is percentage-of-X-ad-spend only; initial beta proposal is 10% of finalized X Ads spend.
- [x] X Ads spend and service fee are itemized separately in reporting/billing rules.
- [x] X Integration review packet and submission cover message are prepared in English.
- [x] Customer onboarding, offboarding, privacy/security, creation, reporting, and pre-sale runbooks are prepared.
- [x] Technical P0 test suite passes in CI on main after merge of PR #53.
- [ ] **X has approved the X Integration in writing.**
- [ ] **One non-owner/customer-like E2E acceptance run has passed on a dedicated deployment against the real X Ads integration.**

## Evidence boundary

Technical P0 completion means the implementation and safety tests pass. It does **not** mean third-party live creation has been proven against X production APIs.

The external/customer-like E2E gate is the evidence that must prove the real sequence:

`request -> settings/preview -> approval hash -> exact approval -> execution key -> exact execution -> PAUSED X creation -> X read-back -> separate activation approval -> X activation -> X read-back`

Do not mark this passed from self-testing, mocks, or code existence.

## P1 — may follow first beta, unless X requires it during review

- [ ] Replace manual customer OAuth provisioning with a full 3-legged OAuth web flow.
- [ ] Automate dedicated deployment provisioning.
- [ ] Add richer visual ad preview and deep links into X Ads Manager.
- [ ] Add direct image/video upload and new Post composition inside the integration.
- [ ] Add automated finalized-spend fee invoicing.
- [ ] Add multi-user roles if a single customer needs multiple End Users.

## External blocking gate

X Ads API Agreement Exhibit A-1 §6.3 requires X approval of the integration before commercialization, marketing, or third-party access. This external approval cannot be bypassed by code.

Apply/coordinate through the X Ads API access/support process and provide the review packet in `docs/X_INTEGRATION_REVIEW_PACKET.md`.

## Go / No-Go

`SELLABLE = TECHNICAL_P0 && X_INTEGRATION_APPROVED && EXTERNAL_E2E_ACCEPTANCE_PASSED`

Until all are true, status is **NO-GO FOR PAID THIRD-PARTY SALE**.
