# AGENTS.md — {{PROJECT_NAME}} AI 向け目次

> **AI エージェント向けの最初の読み物です。** このファイルを読み終えたら ARCHITECTURE.md へ進んでください。

---

## 0. Quick Start（4ステップ）

1. **このファイルを読む** — 鉄則・ジャンプ先・規約を把握する
2. **`ARCHITECTURE.md`** を読む — システム図とドメイン分解を把握する
3. **`docs/design-docs/core-beliefs.md`** を読む — 設計意図と「なぜ」を理解する
4. **該当タスクにジャンプ** — 下記「頻出タスク別ジャンプ先」を参照する

---

## 0.1 コーディングの鉄則（違反 = PR 却下）

| # | 鉄則 | 理由 |
|---|---|---|
| 1 | **{{RULE_1}}** | {{RULE_1_REASON}} |
| 2 | **{{RULE_2}}** | {{RULE_2_REASON}} |
| 3 | **{{RULE_3}}** | {{RULE_3_REASON}} |
| 4 | **ステップキャッシュ必須**: 各ドメインの出力をキャッシュし再実行可能にする | 重い処理の再実行コスト削減 |
| 5 | **テストなし実装禁止**: テストを省略した PR はマージしない | TDD 推奨 |

---

## 0.2 頻出タスク別ジャンプ先

| タスク | 参照先 |
|---|---|
| パイプライン全体を理解したい | `ARCHITECTURE.md` → `docs/DESIGN.md` |
| {{TASK_1}} | {{TASK_1_REF}} |
| {{TASK_2}} | {{TASK_2_REF}} |
| 新機能を追加したい | `/kiro-spec-init "説明"` から SDD フローを開始 |
| バグを修正したい | 該当ドメインのファイル → テスト追加 → 修正 |
| 進行中タスクを確認したい | `docs/exec-plans/active/` |

---

## 0.3 ファイル変更時チェックリスト

```
{{PRIMARY_CODE_DIR}}/ を変更する場合:
  [ ] 対応するユニットテストを tests/unit/ に追加・更新した
  [ ] print() を使っていない（{{LOGGER}} を使う）

config/ を変更する場合:
  [ ] 関連ドキュメントと整合しているか確認した

docs/ を変更する場合:
  [ ] AGENTS.md の「重要ファイル早見表」リンクが生きているか確認した

新機能を追加する場合:
  [ ] /kiro-spec-init で仕様書を作成してから実装した
  [ ] docs/exec-plans/active/ にタスクを記録した
```

---

## 0.4 更新履歴

| 日付 | 変更内容 | 担当 |
|---|---|---|
| {{DATE}} | 初版作成 | AI |

---

## 1. プロジェクト概要

**{{PROJECT_NAME}}** — {{PROJECT_DESCRIPTION}}

---

## 2. リポジトリ構造マップ

```
{{PROJECT_ROOT}}/
├── AGENTS.md                    ← この AI 向け目次
├── ARCHITECTURE.md              ← システム図・ドメイン分解
├── .github/
│   ├── copilot-instructions.md  ← Copilot 全セッション共通ルール
│   ├── prompts/                 ← kiro SDD コマンド群
│   └── agents/                  ← 専門家エージェント
├── .kiro/
│   ├── steering/                ← AI 向けプロジェクト知識
│   ├── specs/                   ← 機能仕様書
│   └── settings/                ← SDD テンプレート・ルール
├── {{PRIMARY_CODE_DIR}}/        ← 実装コア
├── config/                      ← 設定ファイル
├── tests/
│   ├── fixtures/
│   ├── unit/
│   └── integration/
├── docs/
│   ├── design-docs/
│   │   └── core-beliefs.md      ← 設計鉄則
│   └── exec-plans/
│       ├── active/
│       └── completed/
└── scripts/
```

---

## 3. 重要ファイル早見表

| ファイル | 目的 |
|---|---|
| `ARCHITECTURE.md` | ASCII システム図・ドメイン分解テーブル |
| `docs/design-docs/core-beliefs.md` | 変えてはいけない設計思想 |
| `docs/DESIGN.md` | フェーズ別詳細設計 |
| `docs/QUALITY_SCORE.md` | 品質スコアの定義・閾値 |
| `.kiro/steering/product.md` | プロダクトの目的・ユースケース |
| `.kiro/steering/tech.md` | 技術スタック・規約・重要技術決定 |
| `.kiro/steering/structure.md` | ディレクトリ構造・命名規則 |
| `.github/copilot-instructions.md` | Copilot 共通ルール（最優先） |

---

## 4. 設計ドキュメント索引

| ドキュメント | 内容 |
|---|---|
| `docs/design-docs/core-beliefs.md` | 設計哲学と根拠 |
| `docs/DESIGN.md` | フェーズ仕様・設定値・品質ゲート |

---

## 5. 実行計画索引

| ディレクトリ | 内容 |
|---|---|
| `docs/exec-plans/active/` | 進行中タスク（フェーズ分解・受け入れ基準付き） |
| `docs/exec-plans/completed/` | 完了タスク（修正内容・検証結果） |

---

## 6. コーディング規約サマリ

### DO ✅

- 公開関数・クラスにすべて型ヒントを付ける
- `{{LOGGER}}` で構造化ログを出力する
- テストフィクスチャを `tests/fixtures/` に格納する
- 外部コマンドには必ず `timeout=` を設定する

### DON'T ❌

- パイプラインコードで `print()` を使う
- ドメイン間を直接 import で結合する
- `{{PRIMARY_CODE_DIR}}/` 配下に一時ファイルを永続化する（`tmp/` を使う）

---

## 7. テスト実行コマンド

```bash
# ユニットテスト
{{TEST_CMD_UNIT}}

# 統合テスト
{{TEST_CMD_INTEGRATION}}

# カバレッジ付き
{{TEST_CMD_COVERAGE}}
```

---

## SDD ワークフロー

| コマンド | 用途 |
|---|---|
| `/kiro-spec-init "説明"` | 新機能仕様を初期化 |
| `/kiro-spec-requirements {feature}` | 要件定義書を生成 |
| `/kiro-validate-gap {feature}` | 既存コードとのギャップ分析 |
| `/kiro-spec-design {feature}` | 設計書を生成 |
| `/kiro-spec-tasks {feature}` | タスク一覧を生成 |
| `/kiro-spec-impl {feature} [tasks]` | TDD 実装 |
| `/kiro-spec-status {feature}` | 進捗確認 |
| `/kiro-steering` | Steering 更新 |
| `/session-end` | セッション終了 + git push |

**開発ルール**:
- 3 フェーズ承認: 要件 → 設計 → タスク → 実装
- 各フェーズで人間レビューが必要
- レスポンスは日本語で生成すること
- specs / steering のドキュメントはすべて日本語で記述すること
