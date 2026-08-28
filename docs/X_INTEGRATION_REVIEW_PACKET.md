# X Integration Review Packet — Ads DaseRu Kun

Status: **SUBMISSION-READY EXCEPT PRIVATE X FORM FIELDS**  
Language: English

## 1. Applicant / Company Service

**Applicant / operator:** 山内 延天（屋号：RS AI）  
**Company/trade name:** RS AI  
**Company X handle:** @ultimate28  
**Support contact:** yamauchi.rts.office@gmail.com  
**Working product name:** Ads DaseRu Kun  
**Internal nickname:** X広告出せる君

The registered/business address is intentionally not committed to this public repository. The same verified address used for the operator's business/Stripe records must be entered directly into X's private application form.

Ads DaseRu Kun is a conversational campaign-management interface for X Ads. A marketer describes the advertising intent in natural language. The service fills known settings, asks only for material missing fields, shows a complete configuration table and creative preview, then requires two explicit human gates before a paid write:

1. approval hash (`XADS-...`) bound to the exact specification;
2. separate short-lived execution key (`RUN-...`) before any paid write is sent.

Approval is not execution. Any material specification mutation invalidates the token chain.

## 2. Customer architecture

Initial paid beta architecture is deliberately narrow: **one Client + one End User = one dedicated deployment**.

Each deployment has:
- its own repository/runtime;
- its own X authorization and X Ads account binding;
- its own secrets and budget ceilings;
- no shared customer data store;
- a pinned X Ads account for writes.

No Client can access another Client's X Ads Data or features. Multi-user-per-Client roles are outside the initial beta scope.

## 3. Authentication and account control

The preferred production authorization model is the advertiser's own OAuth authorization, consistent with X Ads API guidance.

The service never asks a Client to paste X passwords, OAuth secrets, consumer secrets, access tokens, or access-token secrets into ChatGPT, GitHub Issues, comments, screenshots, or logs.

For the first reviewed beta, authorization material is provisioned into the Client's dedicated secret store. The Client retains direct access to X Ads Manager and can disassociate the service by revoking the connected application in X and disabling/removing the dedicated deployment.

## 4. Campaign management capabilities

Current paid-beta campaign-management surface includes:
- create a bounded website-traffic campaign bundle in `PAUSED` state;
- create its line item in `PAUSED` state;
- attach explicit targeting criteria;
- associate confirmed existing published X Post IDs as promoted Posts;
- read back the X-side campaign, line item, targeting, and promoted Post state;
- separately activate the already-reviewed PAUSED campaign bundle after a new approval/execution flow;
- pause campaign;
- resume campaign;
- change campaign daily budget;
- pause line item;
- resume line item;
- change line-item daily budget.

The initial new-campaign beta is intentionally limited to the supported website-traffic contract and existing published X Posts rather than unrestricted creative generation.

Creation and activation are separate operations. New bundles are created PAUSED and are not activated by the creation approval itself.

## 5. Human authority and safety controls

Every paid state-changing action is subject to:
- dedicated account pinning;
- master write kill switch;
- maximum daily-budget breaker;
- maximum total-budget breaker for new beta bundles;
- command-bound proposal token;
- command-bound approval hash;
- exact user approval text;
- separate command/approval-bound execution key;
- short execution expiry;
- newly-opened execution event only;
- post-write read-back where available.

Read/analysis operations never imply authorization to spend.

The production GitHub Actions route has also been smoke-tested at proposal stage with `write_executed=false` and `delivery_started=false` before any X-side creation.

## 6. Reporting and transparency

The customer reporting surface is designed around the X Ads Analytics metric groups applicable to the selected entity/objective:
- ENGAGEMENT
- BILLING
- VIDEO
- MEDIA
- WEB_CONVERSION
- MOBILE_CONVERSION
- LIFE_TIME_VALUE_MOBILE_CONVERSION

For the initial website-traffic beta, the service uses the X-native groups required to report the applicable X-defined objective metrics, including engagement/click, billing/spend, and web-conversion/site-visit information when available. Unsupported or unavailable data is shown as unavailable rather than silently replaced with third-party values.

If the service displays a third-party or first-party measurement value that corresponds to an X-defined metric, the X-native metric remains identifiable alongside it where required by X's reporting/display rules.

Any service-fee statement or invoice itemizes X Ads spend separately from the Company Service fee. The UI discloses that recent metrics may be provisional and that billed spend may be adjusted/finalized after delivery.

## 7. Pricing

Initial beta pricing proposed for X review:

**Company Service fee: 10% of finalized X Ads spend managed through the service.**

No separate premium is charged for access to X Ads Data. X Ads spend and the Company Service fee are itemized separately.

## 8. Data handling

- Customer data is isolated per dedicated deployment.
- X Materials are used only for the X Ads workflow and reporting.
- Secrets are not persisted in conversational messages, Issues, comments, screenshots, or customer reports.
- X Materials are deleted when no longer needed and in accordance with applicable contractual retention limits.
- A Client offboarding process removes local credentials/data that are no longer required and instructs the Client to revoke the X-connected application.
- Security incidents involving X Materials are escalated according to the then-current X Ads API agreement and applicable law.

Public privacy policy:
`https://github.com/nobutakayamauchi/x-ads-bridge/blob/main/docs/PRIVACY_POLICY.md`

## 9. Branding

The service is not represented as an official X product or as an X Marketing Partner unless X separately grants that status. Public naming, marks, logos, screenshots, and partnership language will follow X Trademark and Brand Guidelines and any feedback from this review.

## 10. Review access

Review materials/source:
`https://github.com/nobutakayamauchi/x-ads-bridge`

Proposal-only production-route smoke-test evidence:
`https://github.com/nobutakayamauchi/x-ads-bridge/issues/56`

For review, we can also provide X with:
- a dedicated review deployment;
- the conversational workflow;
- configuration/status table;
- approval-hash and execution-key flow;
- PAUSED creation/read-back flow;
- separate activation flow;
- read-only analytics/reporting flow;
- source code relevant to the X Ads API integration;
- a bounded demonstration using an authorized Ads account.

A dedicated live review URL will be supplied privately if X requires one; this packet does not claim that the public GitHub repository itself is a hosted Ads execution service.

## 11. Requested approval

We request written approval of the X Integration described above for commercialization to Clients under the applicable X Ads API agreement.

We have not opened paid third-party access and will not commercialize the X Ads API integration before receiving the required written approval.

We are prepared to make any changes X requires before third-party commercialization.

## 12. Submission fields

### Filled from verified business/public records

- Applicant/operator: **山内 延天（屋号：RS AI）**
- Company/trade name: **RS AI**
- Company X handle: **@ultimate28**
- Support contact: **yamauchi.rts.office@gmail.com**
- Review/source URL: **https://github.com/nobutakayamauchi/x-ads-bridge**
- Privacy-policy URL: **https://github.com/nobutakayamauchi/x-ads-bridge/blob/main/docs/PRIVACY_POLICY.md**
- Product/demo evidence: **https://github.com/nobutakayamauchi/x-ads-bridge/issues/56** plus dedicated review demo available on request

### Enter privately in X's form; do not commit to this public repository

- **Registered/business address:** use the exact current address already used in the operator's verified business/Stripe records.
- **Developer App ID:** copy the exact App ID from the X Developer Console for the App whose credentials are used by this integration.
- **Ads API access level/tier:** copy the exact current label shown by X for that App/account or select the access requested in X's application form; do not infer the label from successful API calls.
- **Private review deployment URL/credentials:** provide only if X requests authenticated review access.

## 13. Submission route

Use X's current Ads API access/support application route and enter the private fields directly in X's authenticated form. Keep the submitted form/email confirmation as evidence for the sellability gate.
