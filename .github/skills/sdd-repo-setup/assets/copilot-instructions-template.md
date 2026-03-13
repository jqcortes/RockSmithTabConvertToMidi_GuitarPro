# GitHub Copilot 指示書 — {{PROJECT_NAME}}

> このファイルは VS Code Copilot が全セッションで自動読み込みします。
> すべての Agent / Spec に共通して適用されるプロジェクトルールです。

---

## プロジェクト概要

{{PROJECT_DESCRIPTION}}
<!-- 例: バンドスコア（ギター楽譜、スキャン PDF/PNG）を MIDI ファイルに自動変換するパイプライン。-->

詳細: `ARCHITECTURE.md` / `docs/design-docs/core-beliefs.md`

---

## 技術スタック

| 層 | 技術 | バージョン |
|---|---|---|
| 言語 | {{LANGUAGE}} | {{VERSION}} |
| {{LAYER_2}} | {{TECH_2}} | {{VER_2}} |
| {{LAYER_3}} | {{TECH_3}} | {{VER_3}} |

---

## アーキテクチャ ドメイン

```
{{DOMAIN_FLOW}}
```
<!-- 例:
入力 (Ingest) → OMR → 変換 (Transform) → 出力 (Render) → 品質 (Quality)
    image_in/    omr_engine/   xml_processor/   midi_out/    scorer/
-->

---

## 設計の鉄則（違反 = PR 却下）

1. **{{RULE_1_TITLE}}**: {{RULE_1_BODY}}
2. **{{RULE_2_TITLE}}**: {{RULE_2_BODY}}
3. **{{RULE_3_TITLE}}**: {{RULE_3_BODY}}
4. **ステップキャッシュ必須**: 各ステップは出力をディスクにキャッシュし、特定ステップからの再実行を可能にする
5. **ドメイン間はファイルパス文字列で疎結合**: 各ドメインは `StepResult(success, output_path, metrics, warnings)` を返す

---

## コーディング規約

### 型・命名
- すべての公開関数・クラスに型ヒントを付ける
- ファイル名: `snake_case.{{EXT}}`
- クラス名: `PascalCase`
- 定数: `UPPER_SNAKE_CASE`

### エラー処理
- パイプラインエラーは `{{BASE_ERROR_CLASS}}` を継承した例外で伝播する
- 外部 API 呼び出しはタイムアウトを必ず設定する

### ログ
- `{{LOGGER}}` で構造化ログを出力する
- プレーンな `print()` をパイプラインコードで使わない

### テスト
- `tests/unit/` にユニットテスト、`tests/integration/` に統合テストを置く
- テストフィクスチャは `tests/fixtures/` に格納する
- TDD 推奨: テストを先に書いてから実装する

---

## 禁止事項

- {{FORBIDDEN_1}}
- {{FORBIDDEN_2}}
- 処理途中の一時ファイルを `pipeline/` 配下に永続化しない（`tmp/` 以下を使う）
- テストを省略した実装 PR はマージしない

---

## Spec-Driven Development コマンド一覧

| コマンド | 用途 |
|---|---|
| `/kiro-spec-init "説明"` | 新しい機能仕様を初期化 |
| `/kiro-spec-requirements {feature}` | 要件定義書を生成 |
| `/kiro-validate-gap {feature}` | 既存コードとのギャップ分析 |
| `/kiro-spec-design {feature}` | 設計書を生成 |
| `/kiro-spec-tasks {feature}` | タスク一覧を生成 |
| `/kiro-spec-impl {feature} [tasks]` | TDD 実装 |
| `/kiro-spec-status {feature}` | 進捗確認 |
| `/kiro-steering` | Steering ドキュメントを生成・更新 |
| `/session-end` | セッション終了・コンテキスト保存 |

Specs は `.kiro/specs/` に、Steering は `.kiro/steering/` に保存される。

---

## Agent Skills（専門家エージェント）

`.github/agents/` に登録済みのエージェントを Copilot Chat で `@エージェント名` として呼び出せます。

| エージェント | ファイル | 使いどころ |
|---|---|---|
| {{AGENT_1_NAME}} | `{{AGENT_1_FILE}}` | {{AGENT_1_USE}} |
| {{AGENT_2_NAME}} | `{{AGENT_2_FILE}}` | {{AGENT_2_USE}} |
