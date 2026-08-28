# X広告出せる君 — Operation Protocol 01

Status: **ADOPTED**  
Protocol ID: `XADS-OP-01`

## Core invariant

> **Approval is not execution.**

有料writeは `仕様確定 → 承認ハッシュ → 正確な承認 → 実行キー → 正確な実行` の順でのみ許可する。

## State flow

`DRAFT → INPUT_REQUIRED → READY_FOR_CONFIRMATION → READY_FOR_APPROVAL → APPROVED_NOT_RUNNING → EXECUTION_READY → EXECUTED → read-back verification`

## Approval hash

仕様をLOCKした後、費用警告を表示してユーザーが承認ハッシュ発行を希望した場合だけ発行する。

形式: `XADS-0123456789ABCDEF`

要求文: `XADS-0123456789ABCDEF で承認`

この文がcharacter-for-characterで一致しない限り承認しない。`OK`、`承認`、`それでいい`、音声認識の推測補完は禁止。

承認後の状態は `APPROVED_NOT_RUNNING`。必ず「まだ広告配信は開始していません」と明示する。

## Execution key

承認後、ユーザーが実行意思を示した場合だけ別の実行キーを発行する。

形式: `RUN-0123456789ABCDEF`

要求文: `RUN-0123456789ABCDEF で実行`

Execution keyはexact commandとverified approval tokenにbindし、default TTLは5分。

正確な実行文が返るまではwriteしない。

## Final write gate

全て必要:

- exact same proposed command
- valid proposal token
- valid approval token
- valid unexpired execution token
- exact `RUN-... で実行`
- newly opened `[xop]` Issue
- repository owner entry
- pinned X Ads account
- `XADS_ALLOW_WRITES=true`
- budget breaker pass
- DA/counter-DA complete
- no post-approval spec mutation

一つでも違えばBLOCK。

## Invalidation

アカウント、対象ID、action、budget、schedule、targeting、Creative/image/copy、LP、objective/goalなど承認対象仕様が変わったら承認ハッシュと実行キーを失効扱いにし、仕様確認からやり直す。

## Read-back

write responseだけでACTIVEと断定しない。実行後、可能ならX Adsを再読込し、status、budget、objective/goal、schedule、servability、targeting/creative、関連Pixel/Eventを確認する。

## Legacy route

`[xads]` はread/proposal/internal approval support用。Operation Protocol 01採用後、legacy workflowからの有料writeは無効化する。有料writeは `[xop]` 最終実行のみ。

## Minimal conversation

```text
User: X広告出せる君でこれ出したい。画像これ。予算2500円。
ChatGPT: [自動補完] [不足だけ質問] [設定一覧/プレビュー] この仕様で確定してよろしいですか？
User: はい
ChatGPT: 広告費が発生します。承認ハッシュを発行します。よろしいですか？
User: はい
ChatGPT: XADS-... で承認
User: XADS-... で承認
ChatGPT: 承認済み。まだ配信は開始していません。実行する場合は実行キーを発行します。
User: 実行
ChatGPT: RUN-... で実行
User: RUN-... で実行
ChatGPT: [write] [read-back] [状態報告]
```
