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
   - `XADS_ALLOW_WRITES`
   - `XADS_REPORT_USERNAME`
   - `XADS_REPORT_PASSWORD`
   - `XADS_SERVICE_FEE_PERCENT` (beta default: `10`)
3. Budget caps are not credentials. The bundle workflow has conservative fail-safe beta defaults when no override is supplied:
   - maximum daily budget: `JPY 2,000`
   - maximum total budget: `JPY 5,000`
4. If the Client-approved limits differ, configure dedicated deployment overrides:
   - `XADS_MAX_DAILY_BUDGET_LOCAL`
   - `XADS_MAX_TOTAL_BUDGET_LOCAL`
   The requested campaign must stay at or below both limits. Prefer the lowest caps that satisfy the agreed first campaign.
5. Never put credentials/tokens/passwords into ChatGPT messages, GitHub Issues, comments, or screenshots.
6. Keep `XADS_ALLOW_WRITES=false` for initial verification.
7. Run `ping` and `list_accounts` read-only checks.
8. Verify the returned account is the intended Client account.
9. Run a read-only campaign/list/stats check.
10. Start `reporting_dashboard.py` on localhost and verify authenticated access. If exposing it outside localhost, place it behind suitable TLS/reverse-proxy controls.
11. Verify all X analytics metric groups are offered by the reporting surface. Metric groups unavailable for that account/campaign must be shown as unavailable rather than silently omitted.
12. Load `skills/x-ads-daseru-kun/SKILL.md` into the Client's ChatGPT/Codex workflow.
13. Run a dry conversational flow through final specification and preview.
14. Confirm approval hash and execution key are separate and that no write occurs before the final execution key.
15. Confirm both Client budget breakers: maximum daily budget and maximum total budget, whether using the conservative defaults or explicit overrides.
16. For a new beta ad, use an existing published X Post ID and create the campaign bundle PAUSED first.
17. Read back campaign, line item, targeting, and promoted Post from X and show the Client the actual X-side state.
18. Only after Client acknowledgement, set `XADS_ALLOW_WRITES=true`.
19. Activation must be a separate proposal/approval/execution flow from creation.
20. Run one bounded acceptance action, then read back the resulting X Ads state.

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
