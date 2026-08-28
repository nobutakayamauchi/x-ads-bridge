# Customer Onboarding — Dedicated Beta Deployment

Goal: onboard one paying Client without sharing credentials or data with any other Client.

## Deployment model

One Client gets one dedicated deployment. Do not place multiple Clients into the same repository, secret store, or pinned X Ads account during beta.

## Prerequisites

The Client must have:
- an X account authorized for the relevant X Ads account;
- an X Ads account in good standing;
- a dedicated deployment/repository they control or can revoke access to;
- a ChatGPT/Codex environment capable of loading the `x-ads-daseru-kun` Skill;
- acceptance of applicable X advertising terms/policies.

The service operator must have written X approval for this X Integration before paid third-party onboarding.

## Setup

1. Create a dedicated private deployment for the Client.
2. Configure only in the Client secret store:
   - `XADS_CONSUMER_KEY`
   - `XADS_CONSUMER_SECRET`
   - `XADS_ACCESS_TOKEN`
   - `XADS_ACCESS_TOKEN_SECRET`
   - `XADS_ACCOUNT_ID`
   - `XADS_MAX_DAILY_BUDGET_LOCAL`
   - `XADS_MAX_TOTAL_BUDGET_LOCAL`
   - `XADS_ALLOW_WRITES`
   - `XADS_REPORT_USERNAME`
   - `XADS_REPORT_PASSWORD`
   - `XADS_SERVICE_FEE_PERCENT` (beta default: `10`)
3. Never put those values into ChatGPT messages, GitHub Issues, comments, or screenshots.
4. Keep `XADS_ALLOW_WRITES=false` for initial verification.
5. Run `ping` and `list_accounts` read-only checks.
6. Verify the returned account is the intended Client account.
7. Run a read-only campaign/list/stats check.
8. Start `reporting_dashboard.py` on localhost and verify authenticated access. If exposing it outside localhost, place it behind suitable TLS/reverse-proxy controls.
9. Verify all X analytics metric groups are offered by the reporting surface. Metric groups unavailable for that account/campaign must be shown as unavailable rather than silently omitted.
10. Load `skills/x-ads-daseru-kun/SKILL.md` into the Client's ChatGPT/Codex workflow.
11. Run a dry conversational flow through final specification and preview.
12. Confirm approval hash and execution key are separate and that no write occurs before the final execution key.
13. Configure and confirm both Client budget breakers: maximum daily budget and maximum total budget.
14. For a new beta ad, use an existing published X Post ID and create the campaign bundle PAUSED first.
15. Read back campaign, line item, targeting, and promoted Post from X and show the Client the actual X-side state.
16. Only after Client acknowledgement, set `XADS_ALLOW_WRITES=true`.
17. Activation must be a separate proposal/approval/execution flow from creation.
18. Run one bounded acceptance action, then read back the resulting X Ads state.

## First paid campaign rule

For the first Client campaign:
- use a hard total budget agreed by the Client;
- show exact campaign/line-item settings before approval;
- create the new campaign and line item PAUSED before any activation;
- show X Ads spend separately from the Company Service fee;
- service fee is calculated as the approved percentage of finalized X Ads spend;
- keep a read-back record after every paid state change.

## Reporting rule

The Client must be able to obtain X-native reporting without asking the operator to manually prepare it. The beta reporting dashboard is read-only and requires authentication.

Recent X analytics/spend may be provisional. The Company Service fee must therefore be presented separately and, for billing, calculated against finalized X Ads spend rather than pretending provisional spend is final.

## Disconnect test

Before first paid use, demonstrate that the Client can:
1. manage the same account directly in X Ads Manager;
2. revoke the connected application in X settings;
3. disable/remove the dedicated deployment;
4. remove the dedicated secrets.

The operator must not block or delay this disassociation.

## Support boundary

The Company Service provides first-line support for the integration. Do not tell the Client that X provides support for the Company Service.

## Acceptance record

Mark the external E2E gate in `SELLABILITY_GATE.md` only after a non-owner/customer-like deployment completes:

`rough request -> settings table -> preview -> approval hash -> exact approval -> execution key -> exact execution -> PAUSED creation/read-back -> separate activation approval -> X activation -> read-back`

without secret leakage or cross-customer access.
