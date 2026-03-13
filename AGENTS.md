# AGENTS.md — band-score-to-midi AI 向け目次

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
| 1 | **タブ譜優先**: 五線譜とタブ譜が共存する場合はタブ譜のフレット情報を pitch の正解とする | 五線譜の音域解釈ミスを防ぐ → `docs/design-docs/core-beliefs.md` |
| 2 | **信頼度に正直に**: `quality_score < 0.5` のノートを MIDI に含めない | 誤出力より警告の方がユーザー体験が良い |
| 3 | **エンジン内部に触れない**: Audiveris CLI のみ使用。Java クラス直接呼び出し禁止 | バージョン依存排除 |
| 4 | **ステップキャッシュ必須**: 各ドメインの出力をディスクにキャッシュし再実行可能にする | OMR 処理は数分かかる |
| 5 | **テストなし実装禁止**: テストを省略した PR はマージしない | TDD 推奨 |

---

## 0.2 頻出タスク別ジャンプ先

| タスク | 参照先 |
|---|---|
| パイプライン全体を理解したい | `ARCHITECTURE.md` → `docs/DESIGN.md` |
| 前処理 (Ingest) を変更したい | `docs/DESIGN.md` § Phase 1 → `docs/phase1-foundation.md` → `pipeline/ingest/` ✅ 実装済み |
| Audiveris 設定を変更したい | `docs/audiveris-cli-reference.md` → `pipeline/omr/config.py` → `config/` 🟡 `instrument_map.yaml` は存在、他設定ファイルは未作成 |
| タブ譜・ギター補正のロジック | `docs/guitar-specific.md` → `.kiro/specs/musicxml-transform/` → `pipeline/transform/` ✅ 実装済み |
| 品質スコアの閾値を変更したい | `docs/QUALITY_SCORE.md` → `pipeline/quality/metrics.py` → `pipeline/quality/judge.py` ✅ 実装済み |
| MIDI 出力フォーマットを変更したい | `docs/DESIGN.md` § Phase 4 → `.kiro/specs/midi-render/` → `pipeline/render/` ✅ 実装済み |
| CLI インターフェースを理解したい | `docs/FRONTEND.md` |
| 既存 spec から実装を始めたい | `.kiro/specs/{feature}/tasks.md` → `spec.json` の承認確認 → `/kiro-spec-impl {feature} 1.1` |
| 新機能を追加したい | `/kiro-spec-init "説明"` から SDD フローを開始 |
| バグを修正したい | 該当ドメインの `pipeline/<domain>/` → テスト追加 → 修正 |
| 進行中タスクを確認したい | `docs/exec-plans/active/` |

---

## 0.3 ファイル変更時チェックリスト

```
pipeline/ を変更する場合:
  [ ] 対応するユニットテストを tests/unit/ に追加・更新した
  [ ] StepResult の型シグネチャを変えた場合は呼び出し元を全て更新した
  [ ] print() を使っていない（structlog を使う）

config/ を変更する場合:
  [ ] docs/audiveris-cli-reference.md と整合しているか確認した

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
| 2026-03-13 | 初版作成・SDD フレームワーク導入・steering 生成 | AI |
| 2026-03-13 | 現状監査・リポジトリ構造マップ更新（未実装ディレクトリ明示）・FRONTEND.md/SPEC_DRIVEN_DEV_GUIDE.md/SKILL.md 追記・core-beliefs 原則数修正 | AI |
| 2026-03-13 | SDD ガイド・コマンド表・exec-plans を現状実装に同期。`/session-end` 依存を除去 | AI |
| 2026-03-13 | Render / Quality / CLI / integration tests の実装完了に合わせて構造説明を同期 | AI |

---

## 1. プロジェクト概要

**band-score-to-midi** — バンドスコア（ギター楽譜、スキャン PDF/PNG）を MIDI ファイルに自動変換するローカル CLI パイプライン。

- Audiveris OMR エンジンで楽譜画像を MusicXML に変換し、MIDI Type 1 として出力する
- ギター TAB 記号を優先的に解釈することで汎用 OMR より高精度なギター MIDI を生成する
- ターゲット: ギタリスト個人ユーザー・DTM 制作者

---

## 2. リポジトリ構造マップ

> ✅ = 実装済み / 🟡 = 一部実装・進行中 / 🔧 = 今後実装

```
band-score-to-midi/
├── AGENTS.md                    ← この AI 向け目次
├── ARCHITECTURE.md              ← システム図・ドメイン分解
├── .github/
│   ├── copilot-instructions.md  ← Copilot 全セッション共通ルール
│   ├── agents/                  ← 専門家エージェント (5 ファイル)
│   ├── prompts/                 ← kiro SDD コマンド群 (11 ファイル)
│   └── skills/
│       └── sdd-repo-setup/      ← SDD リポジトリセットアップスキル
├── .kiro/
│   ├── steering/                ← AI 向けプロジェクト知識
│   │   ├── product.md
│   │   ├── tech.md
│   │   └── structure.md
│   ├── specs/                   ← SDD 機能仕様書（phase1-foundation / omr-engine-integration / musicxml-transform / midi-render / quality-scoring）
│   └── settings/                ← SDD テンプレート・ルール
├── pipeline/                    ← 実装コア
│   ├── common.py                ←   StepResult / PipelineError / structlog 設定
│   ├── __main__.py              ←   CLI エントリポイント (`convert` / `quality`)
│   ├── ingest/                  ←   ✅ PDF/PNG → 前処理済み PNG
│   ├── omr/                     ←   ✅ Audiveris CLI ラッパー
│   ├── transform/               ←   ✅ Quality gate 付き MusicXML 補正
│   ├── render/                  ←   ✅ MusicXML → MIDI Type 1
│   └── quality/                 ←   ✅ 品質スコア・レポート
├── config/                      ← 🟡 設定ファイル群（`instrument_map.yaml` のみ存在）
│   └── instrument_map.yaml
├── tests/                       ← テスト
│   ├── fixtures/                ←   ✅ PDF/PNG / MusicXML サンプルあり
│   ├── unit/                    ←   ✅ common / ingest / omr / transform / render / quality / CLI テスト
│   └── integration/             ←   ✅ CLI 連携テストあり
├── docs/
│   ├── DESIGN.md                ← 詳細設計書
│   ├── FRONTEND.md              ← CLI インターフェース仕様
│   ├── QUALITY_SCORE.md         ← 品質スコア定義
│   ├── SPEC_DRIVEN_DEV_GUIDE.md ← SDD 導入ガイド
│   ├── audiveris-cli-reference.md
│   ├── guitar-specific.md
│   ├── omr-pipeline.md
│   ├── phase1-foundation.md
│   ├── design-docs/
│   │   └── core-beliefs.md      ← 設計鉄則（変更要チームレビュー）
│   └── exec-plans/
│       ├── tech-debt-tracker.md ← 技術的負債トラッカー
│       ├── active/              ← musicxml-transform などの進行中タスク
│       └── completed/           ← phase1-ingest などの完了タスク
└── scripts/                     ← 補助スクリプト
    └── create_fixtures.py
```

---

## 3. 重要ファイル早見表

| ファイル | 目的 |
|---|---|
| `ARCHITECTURE.md` | ASCII システム図・ドメイン分解テーブル・依存バージョン |
| `docs/design-docs/core-beliefs.md` | 変えてはいけない設計思想 6 原則 |
| `docs/DESIGN.md` | フェーズ別詳細設計（前処理・OMR・変換・レンダー） |
| `docs/FRONTEND.md` | CLI インターフェース仕様（サブコマンド・オプション定義） |
| `docs/QUALITY_SCORE.md` | 品質スコアの定義・数式・閾値 |
| `docs/SPEC_DRIVEN_DEV_GUIDE.md` | SDD フレームワーク導入ガイド（kiro コマンド・3フェーズ承認） |
| `docs/audiveris-cli-reference.md` | Audiveris CLI コマンドリファレンス |
| `docs/guitar-specific.md` | チョーキング等 ギター特有処理の仕様 |
| `docs/omr-pipeline.md` | OMR パイプライン詳細フロー |
| `docs/phase1-foundation.md` | Phase 1 基盤設計（Ingest ドメイン詳細） |
| `.kiro/specs/musicxml-transform/tasks.md` | Transform ドメインの SDD 実装タスク一覧 |
| `.kiro/specs/midi-render/tasks.md` | Render ドメインの SDD 実装タスク一覧 |
| `.kiro/specs/quality-scoring/tasks.md` | Quality ドメインの SDD 実装タスク一覧 |
| `.kiro/steering/product.md` | プロダクトの目的・ユースケース |
| `.kiro/steering/tech.md` | 技術スタック・規約・重要技術決定 |
| `.kiro/steering/structure.md` | ディレクトリ構造・命名規則 |
| `.github/copilot-instructions.md` | Copilot 共通ルール（最優先） |
| `.github/skills/sdd-repo-setup/SKILL.md` | SDD リポジトリセットアップ・更新スキル |

---

## 4. 設計ドキュメント索引

| ドキュメント | 内容 |
|---|---|
| `docs/design-docs/core-beliefs.md` | Belief 1〜6: 設計哲学と根拠 |
| `docs/DESIGN.md` | Phase 1〜5 の詳細仕様・設定値・品質ゲート |
| `docs/FRONTEND.md` | CLI インターフェース設計（サブコマンド・I/O 仕様） |
| `docs/omr-pipeline.md` | Audiveris OMR パイプラインの詳細 |
| `docs/guitar-specific.md` | TAB 解析・奏法 MIDI マッピング仕様 |
| `docs/phase1-foundation.md` | Phase 1 基盤設計（Ingest ドメイン） |

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
- `structlog` で構造化 JSON ログを出力する
- 各ドメインは `StepResult(success, output_path, metrics, warnings)` を返す
- 外部コマンドには必ず `timeout=` を設定する
- `PipelineError` を継承した例外でエラーを伝播する
- テストフィクスチャを `tests/fixtures/` に格納する

### DON'T ❌

- パイプラインコードで `print()` を使う
- `import torch` を Main Process で使う
- Audiveris の Java 内部クラスを直接呼び出す
- `pipeline/` 配下に一時ファイルを永続化する（`tmp/` を使う）
- ドメイン間を直接 import で結合する

---

## 7. テスト実行コマンド

```bash
# ユニットテスト
python -m pytest tests/unit/ -v

# 統合テスト
python -m pytest tests/integration/ -v

# カバレッジ付き
python -m pytest tests/ --cov=pipeline --cov-report=term-missing

# 特定ドメインのみ
python -m pytest tests/unit/test_transform/test_errors.py -v
```

---

## SDD ワークフロー

| コマンド | 用途 |
|---|---|
| `/kiro-spec-init "説明"` | 新機能仕様を初期化 |
| `/kiro-spec-requirements {feature}` | 要件定義書を生成 |
| `/kiro-validate-gap {feature}` | 既存コードとのギャップ分析 |
| `/kiro-spec-design {feature}` | 設計書を生成 |
| `/kiro-validate-design {feature}` | 設計レビューと実装準備確認 |
| `/kiro-spec-tasks {feature}` | タスク一覧を生成 |
| `/kiro-spec-impl {feature} [tasks]` | TDD 実装 |
| `/kiro-validate-impl {feature}` | 実装が要件を満たすか確認 |
| `/kiro-spec-status {feature}` | 進捗確認 |
| `/kiro-steering` | Steering 更新 |

**開発ルール**:
- 3 フェーズ承認: 要件 → 設計 → タスク → 実装
- `/kiro-spec-impl` 実行前に `spec.json` の `approvals.tasks.approved` を確認すること
- 各フェーズで人間レビューが必要（`-y` は意図的な高速化時のみ）
- レスポンスは日本語で生成すること
- specs / steering のドキュメントはすべて日本語で記述すること
- このリポジトリではセッション終了時の記録は `docs/exec-plans/` と `.kiro/specs/` を手動更新すること
