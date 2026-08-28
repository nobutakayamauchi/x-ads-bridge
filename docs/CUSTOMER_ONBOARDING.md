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
   - `XADS_ALLOW_WRITES`
3. Never put those values into ChatGPT messages, GitHub Issues, comments, or screenshots.
4. Keep `XADS_ALLOW_WRITES=false` for initial verification.
5. Run `ping` and `list_accounts` read-only checks.
6. Verify the returned account is the intended Client account.
7. Run a read-only campaign/list/stats check.
8. Load `skills/x-ads-daseru-kun/SKILL.md` into the Client's ChatGPT/Codex workflow.
9. Run a dry conversational flow through final specification and preview.
10. Confirm approval hash and execution key are separate and that no write occurs before the final execution key.
11. Configure the Client's maximum daily budget ceiling.
12. Only after Client acknowledgement, set `XADS_ALLOW_WRITES=true`.
13. Run one bounded acceptance action, then read back the resulting X Ads state.

## First paid campaign rule

For the first Client campaign:
- use a hard total budget agreed by the Client;
- show exact campaign/line-item settings before approval;
- show X Ads spend separately from the Company Service fee;
- service fee is calculated as the approved percentage of finalized X Ads spend;
- keep a read-back record after every paid state change.

## Support boundary

The Company Service provides first-line support for the integration. Do not tell the Client that X provides support for the Company Service.

## Acceptance record

Mark the external E2E gate in `SELLABILITY_GATE.md` only after a non-owner/customer-like deployment completes:

`rough request -> settings table -> preview -> approval hash -> exact approval -> execution key -> exact execution -> X write -> read-back`

without secret leakage or cross-customer access.
