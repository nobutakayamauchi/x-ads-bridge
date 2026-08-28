# Launch Status

Current status: **NOT YET SELLABLE TO THIRD PARTIES**

The fastest compliant beta technical surface is implemented and CI-tested. Paid third-party launch remains blocked by external evidence gates.

## Technical P0 — complete

- [x] executable new website-traffic campaign bundle creation in PAUSED state;
- [x] campaign/line-item/targeting/promoted-Post read-back;
- [x] partial-creation reporting with no automatic destructive rollback;
- [x] separate approval-gated activation of the created bundle;
- [x] activation precondition requires both campaign and line item PAUSED;
- [x] daily and total budget breakers;
- [x] approval hash and separate short-lived execution key;
- [x] authenticated read-only X-native reporting dashboard;
- [x] all documented X analytics metric groups offered individually, with unsupported groups surfaced as unavailable;
- [x] X Ads spend and Company Service fee itemized separately;
- [x] CI tests covering creation, partial failure, activation safety, approval/execution separation, reporting, and sellability guards.

## Remaining external gates

1. **Written X approval of the X Integration.**
2. **One customer-like E2E acceptance run on a dedicated deployment.**

These are evidence gates, not implementation TODOs. Do not replace them with self-attestation.

## Machine gate

`python sellability_audit.py`

must remain `NO_GO` until both external gates have real evidence. Only then may the corresponding deployment values be set true and the audit become `GO`.
