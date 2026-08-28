# X広告出せる君 — 操作プロトコル01

Protocol ID: `XADS-OP-01`

X Adsの会話型出稿UXを定義する正式プロトコル。

Canonical Skill:
- `skills/x-ads-daseru-kun/SKILL.md`
- `skills/x-ads-daseru-kun/references/OPERATION_PROTOCOL_01.md`

核心ルール:

> **承認と実行を分離する。**

有料writeは以下の順でのみ進める。

`仕様作成 → 一覧/プレビュー → 仕様確定 → 承認ハッシュ発行 → 正確な承認 → 実行キー発行 → 正確な実行 → write → read-back`

User-facing keys:

- Approval hash: `XADS-...`
- Execution key: `RUN-...`

承認済みでも `RUN-... で実行` が正確に返るまでは広告費を発生させない。

旧 `APPROVAL_PROTOCOL.md` は低レベルBridgeの内部トークン仕様として残す。
ユーザー向け操作と有料writeの正規経路はOperation Protocol 01を優先する。
