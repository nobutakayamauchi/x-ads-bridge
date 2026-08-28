# X Integration Review Packet — Ads DaseRu Kun

Status: **DRAFT FOR SUBMISSION TO X**
Language: English

## 1. Company Service

**Working product name:** Ads DaseRu Kun

**Internal nickname:** X広告出せる君

Ads DaseRu Kun is a conversational campaign-management interface for X Ads. A marketer describes the advertising intent in natural language. The service fills known settings, asks only for material missing fields, shows a complete configuration table and creative preview, then requires two explicit human gates before a paid write:

1. approval hash (`XADS-...`) bound to the exact specification;
2. separate short-lived execution key (`RUN-...`) before any paid write is sent.

Approval is not execution. Any material specification mutation invalidates the token chain.

## 2. Customer architecture

Initial beta architecture is **one Client = one dedicated deployment**.

Each deployment has:
- its own repository/runtime;
- its own X developer/app authorization and X Ads account binding;
- its own secrets and budget ceiling;
- no shared customer data store;
- a pinned X Ads account for writes.

No Client can access another Client's X Ads Data or features.

## 3. Authentication and account control

The preferred production authorization model is the advertiser's own OAuth authorization, consistent with X Ads API guidance.

The service never asks a Client to paste X passwords, OAuth secrets, or access tokens into ChatGPT, GitHub Issues, comments, or logs.

For the first reviewed beta, credentials are provisioned into the Client's dedicated secret store. The Client retains direct access to X Ads Manager and can disassociate the service by revoking the connected application in X and disabling/removing the dedicated deployment.

## 4. Campaign management capabilities

Current write capabilities:
- pause campaign;
- resume campaign;
- change campaign daily budget;
- pause line item;
- resume line item;
- change line-item daily budget.

Prepared campaign factory capabilities are kept PAUSED by default before activation. Paid activation remains separately approval-gated.

## 5. Human authority and safety controls

Every paid state-changing action is subject to:
- dedicated account pinning;
- master write kill switch;
- configured daily-budget breaker;
- command-bound proposal token;
- command-bound approval hash;
- exact user approval text;
- separate command/approval-bound execution key;
- short execution expiry;
- newly-opened execution event only;
- post-write read-back where available.

Read/analysis operations never imply authorization to spend.

## 6. Reporting and transparency

The customer reporting surface is designed to expose X-native campaign data and all metric groups available for campaign and line-item analytics:
- ENGAGEMENT
- BILLING
- VIDEO
- MEDIA
- WEB_CONVERSION
- MOBILE_CONVERSION
- LIFE_TIME_VALUE_MOBILE_CONVERSION

Metric applicability depends on campaign objective and account capabilities. Reporting will display X-native metrics and derived metrics only under the X Analytics definitions. Any service-fee statement or invoice itemizes X Ads spend separately from the Company Service fee.

The UI discloses that recent metrics may be provisional and that billed spend may be adjusted/finalized after delivery.

## 7. Pricing

Initial beta pricing proposed for X review:

**Company Service fee: 10% of finalized X Ads spend managed through the service.**

No separate premium is charged for access to X Ads Data. X Ads spend and the Company Service fee are itemized separately.

## 8. Data handling

- Customer data is isolated per dedicated deployment.
- X Materials are used only for the X Ads workflow and reporting.
- Secrets are not persisted in conversational messages or Issues.
- X Materials are deleted when no longer needed and no later than the contractual retention ceiling.
- A Client offboarding process removes local credentials/data and instructs the Client to revoke the X-connected app.
- Security incidents involving X Materials are escalated according to the Ads API Agreement notice requirements.

## 9. Branding

The service is not represented as an official X product or as an X Marketing Partner unless X separately grants that status. Public naming, marks, logos, screenshots, and partnership language will follow X Trademark and Brand Guidelines and any feedback from this review.

## 10. Review access

For review, we can provide X with:
- access to a dedicated review deployment;
- the conversational workflow;
- configuration/status table;
- approval-hash and execution-key flow;
- read-only analytics/reporting flow;
- source code relevant to the X Ads API integration;
- a demonstration using a bounded test Ads account.

## 11. Requested approval

We request written approval of the X Integration described above for commercialization to Clients under the X Ads Products and Services Agreement.

We are prepared to make any changes X requires before third-party commercialization.

## 12. Submission checklist

Before submission, fill:
- Company/legal entity name: **TBD**
- Company X handle: **TBD**
- Developer App ID: **TBD**
- Ads API access tier: **Standard Access requested/confirmed**
- Review deployment URL: **TBD**
- Support contact: **TBD**
- Privacy-policy URL: **TBD**
- Product screenshots/demo: **TBD**

Ads API access/support starting point: `ads.x.com/help`.
