# X Ads API Integration Review — Submission Message

Use this as the English cover note when submitting the integration for review.

---

Subject: Request for X Ads API Integration Review — Ads DaseRu Kun / RS AI

Hello X Ads API team,

I am requesting review and written approval of my X Ads API integration before commercializing it to third-party advertisers.

Applicant/operator: **山内 延天（屋号：RS AI）**  
Trade name: **RS AI**  
X handle: **@ultimate28**  
Product: **Ads DaseRu Kun** (internal nickname: X広告出せる君)

The product is a conversational campaign-management interface. It helps an advertiser prepare X Ads settings, displays the complete proposed configuration, and requires two separate explicit human gates before a paid write: a specification-bound approval hash and a separate short-lived execution key.

For the initial beta, one Client and one End User receive one dedicated deployment, dedicated secret store, and pinned X Ads account. Client data is not shared across deployments. Clients retain direct access to X Ads Manager and can disconnect the integration by revoking the connected application and disabling/removing their dedicated deployment.

The initial new-campaign flow is deliberately narrow. It can prepare and create a bounded website-traffic campaign and line item in PAUSED state, attach explicit targeting and confirmed existing published X Posts, then read the X-side objects back for review. Activation is a separate approval/execution operation after PAUSED-state verification.

The reporting surface is designed around X-native Ads API metrics and the metric groups applicable to the campaign objective/entity. X Ads media spend is itemized separately from our Company Service fee. Unsupported X-native data is shown as unavailable rather than silently substituted.

Proposed beta Company Service fee: **10% of finalized X Ads spend managed through the service**.

I have not opened paid third-party access and will not commercialize the X Ads API integration before receiving the required written approval.

Review/source materials:
https://github.com/nobutakayamauchi/x-ads-bridge

Privacy policy:
https://github.com/nobutakayamauchi/x-ads-bridge/blob/main/docs/PRIVACY_POLICY.md

Proposal-only production-route smoke-test evidence (`write_executed=false`, `delivery_started=false`):
https://github.com/nobutakayamauchi/x-ads-bridge/issues/56

I can provide a dedicated review deployment, authenticated review access, additional screenshots/demo, and a bounded demonstration using an authorized Ads account if required.

Company/legal applicant: **山内 延天（屋号：RS AI）**  
Company X handle: **@ultimate28**  
Developer App ID: **[ENTER DIRECTLY FROM X DEVELOPER CONSOLE]**  
Registered/business address: **[ENTER PRIVATELY IN X FORM USING CURRENT VERIFIED BUSINESS RECORD]**  
Ads API access level: **[COPY EXACT CURRENT/REQUESTED LABEL FROM X]**  
Review/source URL: **https://github.com/nobutakayamauchi/x-ads-bridge**  
Support contact: **yamauchi.rts.office@gmail.com**  
Privacy policy URL: **https://github.com/nobutakayamauchi/x-ads-bridge/blob/main/docs/PRIVACY_POLICY.md**

Please let me know the appropriate next step and any changes required for approval.

Thank you.

山内 延天  
RS AI  
yamauchi.rts.office@gmail.com

---
