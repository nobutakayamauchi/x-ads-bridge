# Reporting Requirements — X Ads API Beta

Customer reporting must be self-serve and must expose X-native metrics available for the selected campaign/line item.

## Metric groups supported by the reporting surface

- `ENGAGEMENT`
- `BILLING`
- `VIDEO`
- `MEDIA`
- `WEB_CONVERSION`
- `MOBILE_CONVERSION`
- `LIFE_TIME_VALUE_MOBILE_CONVERSION`

Not every group is applicable to every campaign objective/account. Unsupported groups must be shown as unavailable/error rather than silently omitted.

## Required disclosures

- X Ads spend is shown separately from Company Service fee.
- Recent analytics can be provisional.
- Billing/spend can be adjusted after delivery and should not be treated as finalized immediately.
- Any third-party metrics shown alongside X metrics must follow the then-current X Analytics Data Display Requirements.

## Beta dashboard

`reporting_dashboard.py` is the initial dedicated-deployment dashboard. It is read-only, authenticated, and defaults to localhost binding. Expose it externally only behind TLS/reverse-proxy controls appropriate for the review/customer deployment.
