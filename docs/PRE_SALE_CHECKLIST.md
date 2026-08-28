# Pre-Sale Checklist — First Customer

Run this immediately before accepting money.

## Regulatory/platform
- [ ] Written X Integration approval retained.
- [ ] Reviewed product/branding/pricing match the approved integration.
- [ ] Ads API access is Standard Access and functioning for the customer deployment.

## Customer deployment
- [ ] Dedicated private deployment created.
- [ ] Dedicated secret store configured.
- [ ] Pinned X Ads account verified.
- [ ] Customer can access X Ads Manager directly.
- [ ] Disconnect/revocation steps demonstrated.
- [ ] No customer secrets appear in chat/issues/logs.

## Product
- [ ] New website-traffic campaign can be created PAUSED.
- [ ] Created campaign/line item/targeting/promoted Post are read back.
- [ ] Activation remains separate from creation.
- [ ] Approval hash and execution key are distinct and exact-match gated.
- [ ] Budget breaker is configured.
- [ ] Read-only reporting dashboard works for X-native metric groups.

## Commercial
- [ ] Fee is 10% of finalized X Ads spend unless a different X-approved percentage is adopted.
- [ ] X Ads spend and service fee are shown separately.
- [ ] Customer understands ad spend is charged by/for X advertising separately from the service fee.
- [ ] Support contact and privacy notice are supplied.

## Evidence
- [ ] `python sellability_audit.py` reports `GO`.
- [ ] External/customer-like E2E acceptance evidence is retained.

If any item is not true, do not accept paid third-party access yet.
