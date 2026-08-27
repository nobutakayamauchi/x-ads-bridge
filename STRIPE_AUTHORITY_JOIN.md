# Stripe Authority Join

Status: **IMPLEMENTED CORE / POSITIVE REALITY PENDING**

## Invariant

A browser-side `purchase_click`, a purchase-complete page, or a paid-looking Stripe record alone must not authorize SCALE.

For WebAI Bridge, an authoritative paid purchase requires all of the following in the same evaluation window:

1. Stripe Checkout Session is live mode.
2. Session is `complete` and `payment_status=paid`.
3. Session uses the canonical WebAI Bridge purchase Payment Link.
4. Session amount/currency exactly match the configured offer.
5. Stripe metadata identifies the canonical product and public-sales purpose.
6. `client_reference_id` matches an owner-excluded funnel session that recorded `purchase_click`.

A paid Stripe session that matches the offer but has no audited browser join is reported as an **unjoined paid candidate** and contributes zero to `stripe_paid_purchases`.

The same rule applies to 0-yen consultation completion, except payment status is not treated as money authority; the Checkout Session must be complete, use the canonical consultation link, carry the expected metadata, and join to an owner-excluded `consult_click` session.

## Reference format

The planned browser join key is:

```text
wab_<random browser session id>
```

It contains no email, name, address, API key, or other customer secret. Stripe Payment Links support `client_reference_id` as a URL parameter for reconciliation.

## Privacy

The authority layer accepts only the Stripe fields required for classification and emits a redacted evidence record. Customer email, name, address, phone, and other customer details are not required for the join and must not be copied into GitHub Issues.

## Decision integration

`authority_audit.audit_with_stripe_authority()` overwrites the proxy-provided Stripe counts with counts derived by `stripe_authority.join_stripe_authority()` before calling `objective_audit.audit_campaign()`.

Therefore an unjoined Stripe payment can never unlock SCALE.

## Reality gates

- Gate A — negative live reality: query the canonical live WebAI Bridge Payment Link. If there are no completed paid Sessions, authoritative purchase count must remain zero even if unrelated live Stripe payments exist elsewhere in the account.
- Gate B — positive zero-cost reality: append the browser join key to the consultation Payment Link, complete the 0-yen consultation flow, and verify exact `consult_click` → `client_reference_id` → completed Checkout Session join.
- Gate C — positive paid reality: only a genuine customer payment (or an intentionally approved paid acceptance test) may prove the paid join. Do not create a paid transaction merely to make the test green.
