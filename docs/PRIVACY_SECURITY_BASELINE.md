# Privacy and Security Baseline — Dedicated Beta

## Secrets

Never put X credentials, passwords, OAuth tokens, consumer secrets, or access-token secrets into ChatGPT messages, GitHub Issues, comments, logs, screenshots, or customer-facing reports.

Secrets belong only in the dedicated Client secret store/runtime environment.

## Isolation

Beta invariant: **one Client = one dedicated deployment + one secret store + one pinned X Ads account**.

No shared cache, database, reporting file, or issue thread may contain X Materials from more than one Client.

## Retention

Delete X Materials when no longer required for the X Ads workflow. Do not retain X Materials beyond the applicable contractual retention ceiling. The current Ads API Agreement requires deletion when there is no legitimate business need and no later than the applicable contractual limits.

## Incident response

If an incident may have exposed X Materials or data related to the integration:
1. stop writes;
2. revoke/rotate affected credentials;
3. preserve minimal incident evidence without expanding exposure;
4. assess affected Clients;
5. notify X within the time required by the then-current Ads API Agreement;
6. notify regulators/Clients where applicable law requires it;
7. document remediation before re-enabling access.

## User data / tracking

If the Company Service collects user data directly or deploys conversion tracking/pixels, publish a legally sufficient privacy notice, obtain any legally required consent, provide required opt-out instructions, and follow X conversion-tracking/ads policies.

## X Materials boundary

Use X Materials only to provide the approved X Ads workflow and reporting. Do not use X Materials to identify/re-identify individuals, enrich unrelated profiles, or train unrelated products.
