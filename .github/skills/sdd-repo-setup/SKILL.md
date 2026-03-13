---
name: sdd-repo-setup
description: 'Harness Engineering スタイルで SDD (Spec-Driven Development) リポジトリ構造をセットアップまたは更新するスキル。Use when: 新しいリポジトリにkiro SDD + Copilot Agent フレームワークを一から構築したい、既存リポジトリのドキュメントや設定ファイルを現在のコードベースの状態に合わせて同期・更新したい、AGENTS.md / copilot-instructions.md / .kiro/steering/ / .github/agents/ などの Copilot カスタマイズファイルを整備したい場合。'
argument-hint: 'モード指定: new (新規構築) | update (既存更新) | agents (エージェント登録のみ)'
---

# SDD リポジトリセットアップスキル

## 概要

このスキルは 2 つのモードで動作する Harness Engineering スタイルの SDD リポジトリ整備ワークフローを提供します。

| モード | トリガーキーワード | 目的 |
|--------|------------------|------|
| **新規構築** (`new`) | 「一から」「最初から」「新規に構築」 | cc-sdd フレームワーク導入 + 全ファイル生成 |
| **既存更新** (`update`) | 「現状に合わせて」「更新して」「同期して」 | 既存ファイルをコードベースの実態に合わせて最新化 |
| **エージェント登録** (`agents`) | 「エージェントを登録」「Agent Skill を追加」 | `.github/agents/` への専門家エージェント追加のみ |

---

## テンプレート & アセット

- [copilot-instructions.md テンプレート](./assets/copilot-instructions-template.md)
- [AGENTS.md テンプレート](./assets/agents-template.md)
- [steering ファイルテンプレート](./assets/steering-template.md)
- [Agent ファイルテンプレート](./assets/agent-template.md)
- [tech-debt-tracker テンプレート](./assets/tech-debt-tracker-template.md)

---

## モード 1: 新規構築 (Fresh Setup)

新しいリポジトリに kiro SDD + Copilot カスタマイズ構造を一から構築する手順。

### ステップ 1: コードベース探索

まず現在のリポジトリ状態を把握する。

```
探索項目:
- プロジェクトの主目的・技術スタック
- 既存の README, docs/, src/ などの構造
- 言語・フレームワーク・依存関係
- 既存の設計ドキュメント
```

### ステップ 2: cc-sdd フレームワーク導入

```bash
npx cc-sdd@latest --copilot --lang ja
```

生成物:
- `.github/prompts/` — kiro SDD コマンドプロンプト群 (11ファイル)
- `.kiro/settings/` — SDD テンプレート・ルール (25ファイル)

> **注意**: cc-sdd は `AGENTS.md` をデフォルトテンプレートで上書きする。後続ステップで Harness Engineering スタイルに更新する。

### ステップ 3: copilot-instructions.md 作成

`.github/copilot-instructions.md` を作成する。[テンプレート](./assets/copilot-instructions-template.md)を参照し以下を含める:

- プロジェクト概要（1段落）
- 技術スタック表（層 | 技術 | バージョン）
- アーキテクチャドメイン図（ASCII art または箇条書き）
- **設計の鉄則**（違反 = PR 却下、5〜7項目）
- コーディング規約（型・命名・エラー処理・ログ・テスト）
- 禁止事項
- SDD コマンド一覧表

### ステップ 4: .kiro/steering/ 3ファイル作成

[テンプレート](./assets/steering-template.md)を参照して作成:

| ファイル | 内容 |
|--------|------|
| `.kiro/steering/product.md` | プロジェクト目的・ターゲットユーザー・ユースケース・スコープ外 |
| `.kiro/steering/tech.md` | 技術スタック詳細・コーディング規約・重要技術決定・パフォーマンス要件 |
| `.kiro/steering/structure.md` | ディレクトリ構造・命名規則・ファイル配置ルール |

### ステップ 5: AGENTS.md を Harness Engineering スタイルに更新

[テンプレート](./assets/agents-template.md)を参照し以下のセクション構成で更新:

1. **Quick Start** (4ステップ)
2. **コーディングの鉄則**（Breaking these = PR rejected）
3. **頻出タスク別ジャンプ先**（タスク | 参照先）
4. **ファイル変更時チェックリスト**
5. **リポジトリ構造マップ**（tree 形式）
6. **重要ファイル早見表**（ファイル | 目的）
7. **設計ドキュメント索引**
8. **実行計画索引**
9. **コーディング規約サマリ**（DO / DON'T）
10. **テスト実行コマンド**
11. **SDD ワークフロー表**

### ステップ 6: docs/ ディレクトリ整備

```
docs/
├── design-docs/
│   └── core-beliefs.md       ← 設計哲学・トレードオフ根拠（既存があれば移動）
└── exec-plans/
    ├── active/
    │   └── <first-phase>.md  ← 最初の実行計画
    ├── completed/             ← (空でOK)
    └── tech-debt-tracker.md  ← [テンプレート](./assets/tech-debt-tracker-template.md)
```

### ステップ 7: エージェントスキル登録

[モード 3](#モード-3-エージェント登録-agents-only) の手順に従い `.github/agents/` にプロジェクト特化エージェントを作成する。

### ステップ 8: copilot-instructions.md に Agent Skills テーブル追記

```markdown
## Agent Skills（専門家エージェント）

`.github/agents/` に登録済みのエージェントを Copilot Chat で `@エージェント名` として呼び出せます。

| エージェント | ファイル | 使いどころ |
|---|---|---|
| ...各エージェントを記載... |
```

### 完了チェックリスト（新規構築）

```
[ ] cc-sdd 実行完了 (.github/prompts/ と .kiro/settings/ が存在)
[ ] copilot-instructions.md に鉄則・禁止事項・SDD コマンド表が含まれる
[ ] .kiro/steering/ に product.md / tech.md / structure.md が揃っている
[ ] AGENTS.md が Harness スタイルの11セクションで構成されている
[ ] docs/design-docs/core-beliefs.md が存在する
[ ] docs/exec-plans/active/ と completed/ が存在する
[ ] docs/exec-plans/tech-debt-tracker.md が存在する
[ ] .github/agents/ に最低3本のエージェントファイルが存在する
[ ] copilot-instructions.md に Agent Skills テーブルがある
```

---

## モード 2: 既存更新 (Update / Sync)

既存リポジトリのドキュメント・設定ファイルをコードベースの現在の状態に合わせて最新化する手順。

### ステップ 1: 現状監査

以下の観点で既存ファイルを検査する:

```
監査項目:
1. copilot-instructions.md の鉄則はコードベースの実装と整合しているか
2. .kiro/steering/ のファイルに新しいドメイン・技術・規約が反映されているか
3. AGENTS.md の重要ファイル早見表に実在しないファイルが記載されていないか
4. docs/exec-plans/active/ のタスクは実際の状況と一致しているか
5. .github/agents/ のエージェントはプロジェクトの現状に対応しているか
```

### ステップ 2: ギャップ分析

監査結果をテーブル形式で整理:

| ファイル | 問題 | 対処 |
|---------|------|------|
| 例: copilot-instructions.md | 新しいドメイン未記載 | 追記 |
| 例: AGENTS.md | Phase 2 完了済みなのに active に残っている | completed に移動 |

### ステップ 3: 優先度順に更新

更新優先度:
1. **最高**: `copilot-instructions.md`（全セッションに影響）
2. **高**: `.kiro/steering/tech.md`（技術的制約・規約の変更）
3. **高**: `AGENTS.md`（AI向け目次の整合性）
4. **中**: `.kiro/steering/structure.md`（構造変更時のみ）
5. **低**: `docs/exec-plans/`（進捗記録）

### ステップ 4: exec-plans の移行

完了したタスクを `active/` → `completed/` に移動し、以下の情報を末尾に追記:

```markdown
## 完了記録

- **完了日**: YYYY-MM-DD
- **実施内容**: （箇条書き）
- **検証結果**: テスト結果・動作確認
```

### 完了チェックリスト（既存更新）

```
[ ] 監査テーブルを作成して全ギャップを把握した
[ ] copilot-instructions.md の鉄則が実装の実態と一致している
[ ] .kiro/steering/ に最新の技術決定が反映されている
[ ] AGENTS.md の全ファイルリンクが実在するパスを指している
[ ] 完了タスクが active/ から completed/ に移動されている
[ ] tech-debt-tracker.md の未解決項目が最新の状態になっている
```

---

## モード 3: エージェント登録 (Agents Only)

### ステップ 1: 必要なエージェントを特定

プロジェクトの技術スタック・ドメインから必要な専門家タイプを洗い出す:

- **アーキテクト系**: ドメイン設計・ADR・トレードオフ分析
- **実装系**: 言語/フレームワーク固有の実装エンジニア
- **レビュー系**: コードレビュー・型チェック・テスト品質
- **ドキュメント系**: ドキュメント維持・API リファレンス
- **品質検証系**: テスト・CI/CD・リリース判定

### ステップ 2: エージェントファイル作成

`.github/agents/<name>.md` に [エージェントテンプレート](./assets/agent-template.md)を使って作成する。

フロントマター形式:
```yaml
---
name: エージェント名（日本語可）
description: エージェントの専門領域と使いどころ（1〜3文）
color: purple   # purple/blue/green/red/orange/yellow/gray
emoji: 🏛️
vibe: |
  キャラクター・口調・判断基準の説明（3〜5文）
---
```

本文構成:
1. `## あなたの役割` — 専門家キャラクター定義
2. `## 専門知識` — 技術スタック・ドメイン知識の箇条書き
3. `## 作業アプローチ` — 優先する思考・判断基準
4. `## 主な作業項目` — 具体的な成果物リスト
5. `## プロジェクト固有の制約` — このリポジトリ固有のルール

### ステップ 3: copilot-instructions.md を更新

`## Agent Skills` テーブルに追加したエージェントを記述する。

---

## 品質基準

| 基準 | 合格条件 |
|------|---------|
| テンプレート準拠 | Harness Engineering スタイルの全セクションを含む |
| リンク整合性 | AGENTS.md 内の全ファイルリンクが実在するパスを指す |
| 現状反映 | steering ファイルが現在のコードベースの技術・構造を正確に記述 |
| エージェント品質 | 各エージェントが明確な専門領域・口調・プロジェクト固有ルールを持つ |
| 鉄則の明確さ | copilot-instructions.md の禁止事項は具体的な理由付きで記述 |
