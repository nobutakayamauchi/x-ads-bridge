# X Ads Bridge — Human Approval Protocol

Status: **FROZEN / ADOPTED**

The bridge may read, analyze, compare, run DA/counter-DA review, and prepare recommendations without write approval. Any operation that changes X Ads state requires the protocol below.

## State machine

### 0. Read / analysis

Allowed without approval:

- read accounts, campaigns, line items, funding instruments, and stats
- calculate CTR, CPC, CPM, spend, budget pacing, and other derived metrics
- identify operational, budget, targeting, duration, or delivery concerns
- perform DA and counter-DA review
- recommend a concrete change

No X Ads write occurs in this stage.

### 1. Proposal

A concrete write command is submitted without approval fields.

The bridge returns:

- `mode=proposal`
- `write_executed=false`
- a fresh randomized 16-character `proposal_token`
- `proposal_expires_at`
- the exact `proposed_command`

The proposal token is cryptographically bound to the exact proposed command and its expiry. Changing the account, target ID, action, amount, expiry, or any other command field invalidates it.

Default proposal lifetime: **60 minutes**.

No formal approval sentence is exposed at this stage.

### 2. Formal approval issuance request

Only after the human explicitly says:

`正式承認文出してください`

may the formal approval issuance step be requested.

The bridge requires all of the following:

- the request text above, exactly
- `da_counter_da_review_complete=true`
- the exact proposed command
- the matching proposal token
- the signed proposal expiry
- the proposal must still be unexpired

If all checks pass, the bridge returns a new randomized 16-character `approval_token`, its expiry, and a formal approval sentence.

The approval token is bound to **both** the exact proposed command and the verified proposal token.

Default formal approval lifetime: **15 minutes**.

Still no X Ads write occurs.

### 3. Human final approval

The human must copy and return the formal approval sentence exactly, for example:

`正式承認コード 0123456789abcdef：広告セット xxxxx の停止を承認します`

Execution requires all of the following at the same time:

- the original proposal token and its signed expiry
- the formal approval token and its signed expiry
- the formal approval must still be unexpired
- `user_approved=true`
- the exact formal approval sentence, character-for-character
- the exact same command that was proposed
- the write master switch enabled
- the write account pinned to `XADS_ACCOUNT_ID`
- a newly **opened** GitHub Issue event
- any applicable budget cap check

Any missing, extra, changed, shortened, mistyped, expired, or mismatched element blocks the write.

Words such as `OK`, `承認`, `やって`, or `それでいい` are never sufficient.

## Safety invariants

1. **Human final authority** — analysis and recommendations may be automated; writes never are.
2. **Two-token chain** — proposal token and approval token are separate randomized values.
3. **Parent binding** — the approval token is bound to the exact proposal token that was verified.
4. **Expiry** — proposal tokens expire by default after 60 minutes; formal approval tokens expire by default after 15 minutes.
5. **Exact-text approval** — no trimming, normalization, fuzzy matching, or speech-intent inference is allowed for the final sentence.
6. **No reopen execution** — reopening an approved Issue cannot execute a write. A write execution must arrive as a newly opened Issue.
7. **Pinned account** — approved writes are blocked unless the requested account equals `XADS_ACCOUNT_ID`.
8. **Master kill switch** — `XADS_ALLOW_WRITES` must be exactly `true` for any write.
9. **Budget breaker** — budget writes are additionally bounded by `XADS_MAX_DAILY_BUDGET_LOCAL`.
10. **Owner-only GitHub entry** — the workflow executes only Issues authored by the repository owner and titled with `[xads]`.
11. **No secrets in Issues** — OAuth secrets and GitHub Secrets must never be written into Issue bodies, comments, logs, or approval text.

## Supported writes

All supported writes use this same approval protocol:

- pause campaign
- resume campaign
- set campaign daily budget
- pause line item / ad set
- resume line item / ad set
- set line item / ad set daily budget

## DA / counter-DA rule

Before requesting a formal approval sentence, review the proposed change for relevant failure modes. At minimum consider, when applicable:

- wrong target or wrong account
- wrong budget amount or unit
- current spend and pacing
- duration / remaining delivery window
- delivery or servability state
- targeting or objective mismatch
- whether the proposed action could make the situation worse
- whether doing nothing is safer

Counter-DA must challenge the DA conclusion before the proposal is promoted to formal approval.

If material uncertainty remains, do not request formal approval; gather more read-only evidence first.
