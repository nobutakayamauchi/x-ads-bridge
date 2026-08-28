# X Ads API Integration Review — Submission Message

Use this as the English cover note when submitting the integration for review.

---

Subject: Request for X Ads API Integration Review — Ads DaseRu Kun

Hello X Ads API team,

We are requesting review and written approval of our X Ads API integration before commercializing it to third-party advertisers.

Product: **Ads DaseRu Kun**

The product is a conversational campaign-management interface. It helps an advertiser prepare X Ads settings, displays the complete proposed configuration, and requires two separate explicit human gates before a paid write: a specification-bound approval hash and a separate short-lived execution key.

Our initial beta architecture is one advertiser/client per dedicated deployment, with a dedicated secret store and a pinned X Ads account. Client data is not shared across deployments. Clients retain direct access to X Ads Manager and can disconnect the integration by revoking the connected application and disabling/removing their dedicated deployment.

The reporting surface is designed around X-native Ads API metrics and the metric groups applicable to campaign and line-item analytics. X Ads media spend is itemized separately from our service fee.

Proposed beta fee: **10% of finalized X Ads spend managed through the service**.

We have not opened paid third-party access and will not commercialize the integration before receiving written approval.

We can provide a review deployment, source code relevant to the integration, screenshots/demo, and a bounded test account. The detailed implementation and compliance summary is available in our review packet.

Please let us know the appropriate next step and any changes required for approval.

Company/legal name: [FILL]
Company X handle: [FILL]
Developer App ID: [FILL]
Ads API access level: [FILL]
Review deployment URL: [FILL]
Support contact: [FILL]
Privacy policy URL: [FILL]

Thank you.

---
