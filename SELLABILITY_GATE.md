# X Ads Bridge — Sellability Gate

Status: **PRE-LAUNCH / X APPROVAL REQUIRED**

This file is the single source of truth for whether the product may be sold to a third party.

## Launch rule

Do **not** commercialize, market, sell, or provide third-party access while any P0 item below is open.

## P0 — must be true before first paid customer

- [x] Conversational operation protocol exists (`skills/x-ads-daseru-kun/SKILL.md`).
- [x] Approval and execution are separate gates (`XADS-...` approval hash, then `RUN-...` execution key).
- [x] Legacy write route cannot perform paid writes; only the current operation-protocol route may reach writes.
- [x] Account pinning, master write switch, budget breaker, exact approval, expiry, and new-issue execution guards remain enforced.
- [x] Deployment model is one customer = one dedicated deployment/repository/secrets set.
- [x] Customer credentials are never requested in ChatGPT messages, GitHub Issues, comments, or logs.
- [x] Customer can disconnect by revoking the app from X Connected Apps and disabling/removing the dedicated deployment.
- [x] Customer-facing reporting specification covers every Ads API metric group applicable to campaign entities.
- [x] Pricing model is percentage-of-X-ad-spend only; initial beta proposal is 10% of finalized X Ads spend.
- [x] X Ads spend and service fee must be itemized separately in any report/invoice.
- [x] X Integration review packet is prepared in English.
- [x] Customer onboarding and offboarding runbooks are prepared.
- [x] Privacy/security baseline and data-retention requirements are documented.
- [ ] **X has approved the X Integration in writing.**
- [ ] **One non-owner/customer-like E2E acceptance run has passed on a dedicated deployment.**

## P1 — may follow first beta, unless X requires it during review

- [ ] Replace manual customer OAuth provisioning with a full 3-legged OAuth web flow.
- [ ] Automate dedicated deployment provisioning.
- [ ] Add richer visual ad preview and deep links into X Ads Manager.
- [ ] Add automated finalized-spend fee invoicing.
- [ ] Add multi-user roles if a single customer needs multiple End Users.

## External blocking gate

X Ads API Agreement Exhibit A-1 §6.3 requires X approval of the integration before commercialization, marketing, or third-party access. This external approval cannot be bypassed by code.

Apply/coordinate through the X Ads API access/support process and provide the review packet in `docs/X_INTEGRATION_REVIEW_PACKET.md`.

## Go / No-Go

`SELLABLE = X_INTEGRATION_APPROVED && EXTERNAL_E2E_ACCEPTANCE_PASSED`

Until both are true, status is **NO-GO FOR PAID THIRD-PARTY SALE**.
