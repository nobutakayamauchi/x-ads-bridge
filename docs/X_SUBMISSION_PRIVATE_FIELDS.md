# X Ads API Review — Private Submission Fields

This file intentionally contains **instructions only**, not the operator's private address, OAuth credentials, or Developer App ID.

Public review materials are safe to keep in this repository. The following values must be copied directly into X's authenticated application/support form and must not be guessed from public artifacts.

## 1. Registered/business address

Use the operator's exact current business/contact address from the verified business record used for Stripe/commerce operations.

Rules:
- copy it exactly;
- do not infer an address from residence city, public posts, location history, or unrelated documents;
- do not commit the full address to this public repository solely for the X review;
- if X asks for proof, provide it through X's private support/review channel.

## 2. Developer App ID

Open the X Developer Console and select the App whose OAuth credentials are actually used by this Ads integration.

Copy the App ID exactly as X displays it. Do not substitute:
- Ads account ID;
- campaign ID;
- OAuth consumer key;
- client ID unless X explicitly labels that value as the requested App ID;
- GitHub repository ID.

## 3. Ads API access level/tier

Copy the exact current access label shown by X for this App/account, or select the access level requested by the X application form.

Successful Ads API calls prove that an integration is currently able to access endpoints; they do not by themselves prove the human-readable access-tier label required by a form.

## 4. Private review deployment

If X requires a hosted review environment, provide its URL and credentials only through X's private review channel. Do not publish review credentials in GitHub.

## 5. Evidence to retain after submission

Keep:
- X submission/support case number;
- submission confirmation email or screenshot;
- exact App ID submitted;
- date submitted;
- version/commit of the review packet submitted;
- X's written approval or requested changes.

Do not set `XADS_X_INTEGRATION_APPROVED=true` until written X approval has actually been received and retained.
