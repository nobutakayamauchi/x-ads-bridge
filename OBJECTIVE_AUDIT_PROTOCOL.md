# X Ads Bridge — Objective-Aligned Funnel Audit

Status: **FROZEN / ADOPTED**

The purpose of an ad campaign is defined by its business objective, not by proxy metrics such as impressions, clicks, CTR, or CPC.

## Core invariant

**A proxy metric may explain what is happening. It may never redefine why the campaign exists.**

For a sales campaign whose primary objective is purchase, cheap clicks with no movement toward purchase are not a scaling signal.

## Funnel authority

For WebAI Bridge public sales, the audit funnel is:

```text
X impressions
→ X link clicks
→ sales LP unique arrivals
→ consultation CTA click / purchase CTA click
→ Stripe consultation completion / Checkout progression
→ authoritative Stripe paid purchase
```

Authority rules:

- X impression/click/spend data: X Ads API authority.
- LP/CTA browser events: funnel telemetry authority after owner-device exclusion.
- Browser purchase-complete page: diagnostic only.
- Paid purchase: Stripe live payment/Checkout authority only.

## Owner-device exclusion

The operator's smartphone receives a random local device identifier. The raw identifier is not stored in analytics records; the server stores an HMAC hash.

Events from excluded operator devices remain available in total/raw counts but are removed from audited counts used for ad decisions.

Do not exclude by iPhone model, User-Agent, IP address, Wi-Fi network, or mobile carrier. Those methods can remove real customers or fail when the operator changes networks.

## Campaign objective contract

Before automatic SCALE decisions are allowed, the campaign must have an explicit objective contract containing at least:

- `primary_objective` — e.g. `purchase`, `consultation`, `lead`;
- `target_count` — required objective completions;
- `max_spend_jpy` and/or another explicit loss boundary;
- `evaluation_window` — the time or sample window used for judgment;
- optional `target_cpa_jpy` / gross-profit constraint;
- optional funnel minimums, if they are meaningful for that campaign.

No hidden default is allowed to silently replace the campaign's stated business purpose.

## Decision states

### SCALE

Allowed only when the primary objective is being achieved and economics remain inside the configured boundaries.

A strong CTR/CPC alone is never enough.

### HOLD

Objective direction is acceptable but evidence is not yet strong enough to increase spend. Continue at the current bounded budget and collect more evidence.

### DIAGNOSE

Proxy metrics are working but the primary objective is not progressing. Examples:

- X clicks are high but LP arrivals are abnormally low;
- LP arrivals occur but consultation/purchase CTA progression is weak;
- purchase CTA progression occurs but Stripe paid purchases do not follow.

Default action: **no budget increase**. Identify and repair the failing funnel stage first.

### STOP

Use when the configured loss/sample boundary is reached without the required primary-objective result, or when continuing would violate the stated purpose/economics.

A campaign may have excellent CTR and still be STOP.

### INSUFFICIENT_EVIDENCE

Use when the objective contract or evidence required for a safe decision is missing. It must never be promoted to SCALE by guessing.

## DA / Counter-DA order

Before any write proposal that increases spend:

1. Verify the campaign's original objective contract.
2. Read X Ads delivery/spend/click evidence.
3. Read owner-excluded funnel evidence.
4. Read authoritative Stripe objective completions.
5. Identify the first meaningful funnel break.
6. DA: argue why increasing spend could be wrong or wasteful.
7. Counter-DA: challenge that conclusion using the available evidence.
8. Return one state: SCALE / HOLD / DIAGNOSE / STOP / INSUFFICIENT_EVIDENCE.
9. Only SCALE may produce a budget-increase proposal.
10. The existing human formal-approval protocol remains mandatory for the actual X Ads write.

## Budget principle

The hard budget ceiling is an accident boundary, not a target.

A high-performing campaign may justify raising its operating budget or even proposing a future hard-ceiling review, but neither happens merely because the current ceiling has been reached. The objective and economics must justify it.
