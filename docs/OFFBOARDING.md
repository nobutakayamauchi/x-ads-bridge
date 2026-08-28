# Customer Offboarding / Disconnect

The Client must be able to quickly regain exclusive direct control of its X Ads account.

## Immediate disconnect

1. Open X settings for connected apps: `https://x.com/settings/connected_apps`.
2. Revoke the application used by the dedicated Ads DaseRu Kun deployment.
3. In the dedicated deployment, set `XADS_ALLOW_WRITES=false` or disable/delete the deployment/workflows.
4. Confirm the Company Service can no longer read or write the Client's X Ads account.

The Client does not need the Company Service to manage campaigns directly in X Ads Manager.

## Data cleanup

After disconnect:
- remove X OAuth/access secrets from the dedicated secret store;
- securely delete cached X Materials when no longer needed;
- retain X Materials no longer than the contractual retention ceiling;
- delete dedicated deployment artifacts that are not required for legal/accounting records;
- do not retain X Materials merely for product training or unrelated analytics.

## Operator rule

The operator must not prevent, delay, or condition Client disassociation on payment, support interaction, or account closure.
