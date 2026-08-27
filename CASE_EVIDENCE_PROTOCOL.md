# X Ads Case Evidence Protocol

## Purpose
Store external X/public evidence only when it can be reconstructed as a reusable advertising experiment case.

The atomic learning unit is not a Post. It is a triad:

1. **Intent** — what the advertiser wanted to achieve / what problem they were trying to solve.
2. **Test** — what they changed, compared, targeted, optimized, or otherwise did to test the intent.
3. **Outcome** — what happened, preferably with quantitative metrics and a comparison/baseline.

A case is `CASE_READY` only when all three are supported by source evidence.

## Evidence classes

- `CASE_READY_VERIFIED`: Intent + Test + Outcome are all present, source identity is coherent, and quantitative claims are internally consistent or independently corroborated.
- `CASE_READY_SELF_REPORTED`: all three are present but results are only self-reported by the advertiser/operator.
- `PARTIAL_CASE`: one or two legs are missing.
- `ANECDOTE`: opinion/advice/claim without reconstructable test and outcome.
- `REJECTED`: irrelevant, contradictory, unverifiable, or too distant from the product/campaign context.

## Required fields

```json
{
  "case_id": "...",
  "source_refs": ["post/thread/case-study refs"],
  "intent": {
    "objective": "lead|purchase|traffic|awareness|other",
    "target_or_problem": "...",
    "evidence": "source-supported summary"
  },
  "test": {
    "changed_dimension": "creative|targeting|optimization_event|bid|LP|offer|other",
    "before_or_control": "...",
    "after_or_challenge": "...",
    "held_constant": [],
    "budget_or_window": "...",
    "evidence": "source-supported summary"
  },
  "outcome": {
    "metrics": {},
    "direction": "improved|worsened|mixed|unknown",
    "evidence": "source-supported summary"
  },
  "verification": {
    "source_type": "official_case|operator_post|company_post|third_party",
    "self_reported": true,
    "numeric_consistency": "pass|fail|not_applicable",
    "cross_source_corroboration": "yes|no|not_checked",
    "case_class": "CASE_READY_SELF_REPORTED"
  },
  "product_fit": {
    "score": 0.0,
    "near_case": false,
    "reasons": []
  }
}
```

## Collection rule

Search should prioritize Posts/threads containing both causal/test language and outcome language, e.g. concepts equivalent to:

- intent: 目的, 狙い, 獲得, 改善したい, 検証したい
- test: A/B, テスト, 変更, 比較, 切り替え, ターゲティング, LP, クリエイティブ, 最適化
- outcome: CPA, CV, CVR, CTR, CPC, CPM, ROAS, 売上, 問い合わせ, %改善, 倍

Do not retain a high-engagement Post merely because it is popular.

## Thread reconstruction

The three legs may exist across multiple Posts in one conversation/thread. The collector may group by conversation/thread identity and promote the group to a case only after the triad is complete.

## Authority rule

External cases may influence hypothesis priority and benchmark expectations. They never authorize SCALE. Own campaign + LP + authoritative conversion/revenue evidence remains the authority for business decisions.
