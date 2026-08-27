# X Ads Evolution Protocol

## Goal

Turn each bounded X Ads run into one of two useful outputs:

1. commercial evidence (the ad produces the configured business outcome inside its spend boundary), or
2. diagnostic evidence (a controlled experiment resolves one hypothesis and narrows the next test).

The system must not treat external X chatter, CTR, CPC, impressions, or other proxy metrics as authority to scale spend.

## Evidence layers

### A. Authority evidence

Only first-party / authoritative business evidence can authorize `SCALE`:

- X Ads spend and delivery metrics joined to the tested campaign
- first-party LP / CTA funnel events
- authoritative consultation completion
- authoritative paid purchase / Stripe evidence

`objective_audit.py` remains the authority gate.

### B. External X signals

Public X data is collected only to generate candidate hypotheses. Sources may include:

- X Recent Search (last 7 days)
- X Filtered Stream later, when continuous monitoring is justified
- public operator case studies
- public expert benchmarks

External signals are inspected against the current product profile before they enter the hypothesis pool.

## Signal inspection metadata

Each signal is reduced to aggregate product-relevant metadata:

- relevance score / band
- matched topic
- matched pain
- matched commercial intent
- offer/CTA match
- evidence quality
- freshness
- candidate experiment dimension

The default privacy posture is **aggregate features only**. Do not build targeting around sensitive personal attributes and do not fetch user profiles unless a future experiment explicitly requires and justifies it.

## Relevance gate

`HIGH` and `MEDIUM` signals may enter the hypothesis pool. `LOW` signals are retained only as rejected evidence.

External signals can nominate:

- `creative_hook`
- `offer_or_cta`
- `targeting_or_message_topic`
- `benchmark`

They cannot authorize campaign scale.

## Cost gate for external X collection

X API Post reads are pay-per-use. The collector therefore defaults to:

- 20 Posts maximum per run
- estimated maximum read cost calculation before execution
- `$0.10` default per-run cost cap
- execution blocked unless `X_SIGNAL_ALLOW_PAID_READS=true`
- no User lookup; collect Post text, time, language and public metrics only

The cost cap is configuration, not a reason to assume credits exist.

## Experiment contract

Every new experiment must freeze all variables except the one being tested.

Record:

- parent/control experiment ID
- hypothesis ID
- changed variable
- fixed variables
- spend cap
- directional checkpoint
- authority objective contract
- diagnostic metric(s)
- preflight gates

## Meaning classification

After the run, classify it separately from the business audit:

### BUSINESS_WIN

The authority audit returns `SCALE`.

This is the only class that can authorize scale.

### DIAGNOSTIC_WIN

The primary objective did not authorize scale, but:

- the planned sample/checkpoint was reached,
- exactly one variable was changed, and
- the stated hypothesis was confirmed or refuted.

This ad was commercially unsuccessful or unfinished, but the spend produced reusable information.

### BUSINESS_LOSS

The spend boundary was reached without the business objective and without resolving the hypothesis.

### INCONCLUSIVE

The sample/control quality is insufficient to draw either a commercial or diagnostic conclusion.

## Evolution loop

```text
External X signals
       |
       v
Inspect against current product profile
       |
       v
Aggregate metadata / reject low relevance
       |
       v
Nominate hypotheses
       |
       v
Choose ONE untested dimension
       |
       v
Create bounded campaign experiment
       |
       v
X Ads metrics + first-party funnel + Stripe
       |
       v
Objective audit (business authority)
       |
       +--> SCALE only on real outcome
       |
       v
Meaning classification
       |
       +--> BUSINESS_WIN
       +--> DIAGNOSTIC_WIN
       +--> BUSINESS_LOSS
       +--> INCONCLUSIVE
       |
       v
Update experiment history and select next unresolved hypothesis
```

## Core invariant

> Every yen should either buy a business outcome or buy a falsifiable piece of information. Proxy metrics and external popularity are never enough to scale by themselves.
