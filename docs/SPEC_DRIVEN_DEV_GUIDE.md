# 仕様駆動開発（Spec-Driven Development）導入ガイド

> **対象**: 開発中の既存リポジトリに kiro スタイルの仕様駆動開発を後付けで導入する手順

---

## 概要

このガイドで実現できること：

- AI（GitHub Copilot）が「何を・なぜ・どう作るか」を常に理解した状態で実装を進められる
- 要件 → 設計 → タスク → 実装（TDD）の段階的なフローが自動化される
- セッションをまたいでもコンテキストが失われない

---

## 前提条件

| 項目 | 要件 |
|-----|-----|
| エディタ | VS Code |
| AI 拡張 | GitHub Copilot（Chat 機能付き） |
| Node.js | v18 以上（`npx` が使えること） |
| Git | 任意のリモートリポジトリ |

---

## Phase 0: フレームワークのインストール

### 0-1. cc-sdd を実行する

```powershell
cd C:\path\to\your-repo
npx cc-sdd@latest --copilot --lang ja
```

**何が作られるか：**

```
.github/
  copilot-instructions.md   ← 既存の場合は確認して手動マージ
  prompts/
    kiro-spec-init.prompt.md
    kiro-spec-requirements.prompt.md
    kiro-spec-design.prompt.md
    kiro-spec-tasks.prompt.md
    kiro-spec-impl.prompt.md
    kiro-spec-status.prompt.md
    kiro-validate-gap.prompt.md
    kiro-validate-design.prompt.md
    kiro-validate-impl.prompt.md
    kiro-steering.prompt.md
    kiro-steering-custom.prompt.md
.kiro/
  settings/
    rules/        ← AI の振る舞いルール
    templates/    ← spec / steering のひな形
```

> ⚠️ `.github/copilot-instructions.md` が既存の場合、上書きを確認されます。既存内容をバックアップしてから実行してください。

### 0-2. copilot-instructions.md を整備する

既存ファイルがあれば内容をマージし、以下の情報を追記・確認します：

```markdown
## プロジェクト概要
（何を作るか 2〜3 行）

## 技術スタック
（言語・フレームワーク・主要ライブラリ）

## 設計原則（鉄則）
（チームの Do / Don't を箇条書きで）

## コーディング規約
（型ヒント・命名規則・テスト方針等）

## 禁止事項
（使ってはいけないライブラリ・パターン）
```

> **なぜ重要か**: このファイルは VS Code Copilot が**全セッションで自動的に読む**唯一のファイルです。steering よりも確実に参照されます。

---

## Phase 1: Steering の生成（任意だが推奨）

> `copilot-instructions.md` が充実している場合はスキップ可。チームで Cursor 等の別 AI ツールも使う場合は必須。

VS Code の Copilot Chat で実行：

```
/kiro-steering
```

AI がコードベースを自動分析し、以下の 3 ファイルを生成します：

| ファイル | 内容 |
|--------|-----|
| `.kiro/steering/product.md` | プロジェクトの目的・価値・ターゲット |
| `.kiro/steering/tech.md` | 技術スタック・アーキテクチャ決定・規約 |
| `.kiro/steering/structure.md` | ディレクトリ構造・命名規則・インポート規則 |

**生成後に必ず人間がレビューして修正してください。** 特に：

- `tech.md`: 実際のバージョン・ライブラリ名と一致しているか
- `structure.md`: 現在の実際のディレクトリ構造と一致しているか
- `product.md`: 「現状」ではなく「意図・目指す姿」が書かれているか

---

## Phase 2: 既存機能のドキュメント化（リバースエンジニアリング）

> 完全に新規フィーチャーから始める場合は Phase 3 にスキップ。

既存の実装済み機能を spec として整理します。

### 2-1. Spec を初期化する

```
/kiro-spec-init "既存の機能名（例: ユーザー認証機能）"
```

作成されるファイル：

```
.kiro/specs/user-auth/
  spec.json          ← メタデータ・フェーズ管理
  requirements.md    ← プロジェクト説明（次のステップで要件に変換）
```

### 2-2. 要件を生成する

```
/kiro-spec-requirements user-auth
```

AI が `requirements.md` を EARS 形式の要件定義書に変換します。  
生成後にレビューし、実態と違う部分を修正してください。

### 2-3. ギャップ分析を実行する ← 既存リポジトリの核心

```
/kiro-validate-gap user-auth
```

AI が「要件に書いたこと」と「実際のコード」を突き合わせ、以下を分析します：

| 分析結果 | 内容 |
|--------|-----|
| 実装済み ✅ | 要件を満たしているコードが存在する |
| 未実装 ❌ | 要件に書いたが実装がない（テスト不足含む） |
| 仕様との乖離 ⚠️ | コードはあるが要件を満たしていない |

未実装・乖離が見つかった場合は、次の Phase 3 でタスク化します。

---

## Phase 3: 新機能の spec 作成（本来のフロー）

### 3-1. 機能の説明から spec を初期化

```
/kiro-spec-init "次に開発する機能の説明をここに詳しく書く"
```

例：
```
/kiro-spec-init "リアルタイム音声変換パイプライン。マイク入力→VAD→推論→再生の一連フローをマルチプロセスで実装。レイテンシ目標 250ms 以内（CPU）"
```

> **コツ**: 説明が詳細なほど生成される要件・設計の質が上がります。箇条書きより文章で書いてください。

### 3-2. 要件定義書を生成

```
/kiro-spec-requirements {feature-name}
```

生成された `requirements.md` をレビュー：

- 「WHEN ... THE SYSTEM SHALL ...」形式（EARS 形式）で書かれているか
- テスト可能な条件になっているか
- スコープが適切か（大きすぎないか）

問題なければ以下で承認：

```
/kiro-spec-requirements {feature-name}
承認します
```

または spec.json の `approvals.requirements.approved` を手動で `true` に変更。

### 3-3. ギャップ分析（既存コードがある場合）

```
/kiro-validate-gap {feature-name}
```

新機能でも既存コードと関連する場合は実行してください。  
**純粋に新規の場合はスキップ可。**

### 3-4. 設計書を生成

```
/kiro-spec-design {feature-name}
```

生成される内容：
- アーキテクチャ概要・コンポーネント構成
- データフロー・シーケンス図
- API インターフェース定義
- 技術的決定とその根拠

レビュー後に承認（コマンド応答で `承認します` または spec.json を手動更新）。

> **`-y` フラグ**: `/kiro-spec-design {feature-name} -y` で人間レビューをスキップして高速化できます。急ぎの場合のみ推奨。

### 3-5. タスク一覧を生成

```
/kiro-spec-tasks {feature-name}
```

生成される `tasks.md` の例：

```markdown
## Task 1: VAD モジュールの実装

- [ ] 1.1 silero-VAD モデルのロードと推論を実装する
- [ ] 1.2 16kHz リサンプリング処理を追加する
- [ ] 1.3 unit test を作成して PASS させる
```

レビューして承認。

---

## Phase 4: TDD 実装

### 4-1. タスクを実行する

```
/kiro-spec-impl {feature-name}
```

**特定タスクのみ実行する場合：**

```
/kiro-spec-impl {feature-name} 1
/kiro-spec-impl {feature-name} 1.1,1.2
/kiro-spec-impl {feature-name} 1,2,3
```

AI が以下の順で実行します：

1. **テストを先に書く**（Red）
2. **最小実装でテストを通す**（Green）
3. コード改善（リファクタリング）は明示的に指示した場合のみ

### 4-2. 進捗を確認する

```
/kiro-spec-status {feature-name}
```

出力例：
```
Tasks: 7/10 completed (70%)
- [x] 1.1 VAD モデルロード
- [x] 1.2 リサンプリング
- [ ] 1.3 unit test ← 次のタスク
```

### 4-3. 実装後の検証（任意）

```
/kiro-validate-impl {feature-name}
```

要件に対する実装の完全性を最終確認します。

### 4-4. spec.json の phase を更新する

このリポジトリでは spec.json の `phase` を次の 4 値で運用します。

| phase 値 | 意味 |
|---|---|
| `requirements-generated` | 要件生成済み。次は設計へ進める |
| `design-generated` | 設計生成済み。次はタスク化へ進める |
| `tasks-generated` | タスク生成済み。次は実装へ進める |
| `implementation-complete` | 実装と検証まで完了した |

補足:

1. `ready_for_implementation: true` は「requirements / design / tasks の承認が揃い、実装に進める状態」を意味する
2. 実装完了後も互換性のため `ready_for_implementation` は `true` のままでよい
3. 全タスク完了、主要テスト PASS、必要な検証が終わったら `phase` を `implementation-complete` に更新する

---

## Phase 5: セッションの手動クローズ

このリポジトリには現時点で `/session-end` prompt が含まれていないため、セッション終端では以下を手動で行います：

1. `docs/exec-plans/active/` もしくは `completed/` を更新する
2. 対象 spec の `tasks.md` / `spec.json` を更新する
3. `spec.json` は少なくとも `updated_at` と `phase` を実態に合わせる
4. `.github/copilot-instructions.md` や `AGENTS.md` に新しい運用知見を反映する
5. Git を使っている場合は `git add -A` → `git commit` → `git push` を手動実行する

---

## 全体フロー図

```
既存リポジトリ
    │
    ▼
Phase 0: npx cc-sdd@latest --copilot --lang ja
    │       └─ .github/prompts/ + .kiro/settings/ を生成
    │
    ▼
Phase 0': copilot-instructions.md を整備（最重要）
    │
    ▼
Phase 1: /kiro-steering（任意）
    │       └─ .kiro/steering/ product/tech/structure を生成
    │
    ├──[既存機能のドキュメント化]──────────────────────┐
    │  Phase 2:                                       │
    │  /kiro-spec-init "既存機能"                     │
    │  /kiro-spec-requirements {feature}              │
    │  /kiro-validate-gap {feature}  ← ★重要          │
    │  → ギャップをタスク化                            │
    └──────────────────────────────────────────────────┘
    │
    ├──[新機能開発]────────────────────────────────────┐
    │  Phase 3:                                       │
    │  /kiro-spec-init "新機能の詳細説明"              │
    │  /kiro-spec-requirements {feature}              │
    │  [/kiro-validate-gap {feature}]  ← 関連あれば   │
    │  /kiro-spec-design {feature}                    │
    │  /kiro-spec-tasks {feature}                     │
    └──────────────────────────────────────────────────┘
    │
    ▼
Phase 4: /kiro-spec-impl {feature} [task-numbers]
    │       └─ TDD: テスト先行 → 実装 → PASS
    │
    ▼
Phase 5: exec-plans / spec.json を手動更新 → 必要なら git push
```

---

## よくある問題と対処

| 問題 | 原因 | 対処 |
|-----|-----|-----|
| AI が古い設計を踏襲している | `copilot-instructions.md` に禁止事項が書かれていない | `## 禁止事項` セクションに明記する |
| 生成された要件がスコープ過大 | `spec-init` の説明が広すぎた | 機能を分割して複数の spec に分ける |
| `validate-gap` で大量の未実装が検出される | 要件が理想的すぎる | 要件を「現実的な MVP」に絞り込む |
| テストが通らない（実装後） | 依存ライブラリのバージョン差 | `copilot-instructions.md` の実行環境セクションにバージョンを明記する |
| セッションをまたいでコンテキストが消える | exec-plan や spec の進捗を残していない | `docs/exec-plans/` と `.kiro/specs/*/tasks.md` を手動更新する |
| `steering` と `copilot-instructions.md` の内容が矛盾する | 更新タイミングのズレ | `copilot-instructions.md` を正とし、steering を `/kiro-steering` で同期する |

---

## チェックリスト（新リポジトリへの適用時）

```
Phase 0
  [ ] npx cc-sdd@latest --copilot --lang ja を実行した
  [ ] .github/copilot-instructions.md の既存内容を保持・マージした
  [ ] copilot-instructions.md に技術スタック・禁止事項・規約を記載した

Phase 1（任意）
  [ ] /kiro-steering を実行した
  [ ] 3 つの steering ファイルを人間がレビュー・修正した

Phase 2（既存機能がある場合）
  [ ] 主要な既存機能を spec-init でドキュメント化した
  [ ] /kiro-validate-gap でギャップ分析を実施した
  [ ] ギャップが tech-debt-tracker.md に記録されている

Phase 3+ (継続開発)
  [ ] 新機能ごとに /kiro-spec-init から始めている
  [ ] 設計・タスクを人間がレビューしてから /kiro-spec-impl を呼んでいる
  [ ] セッション終了時に `docs/exec-plans/` と必要な spec ファイルを更新している
```

---

## 付録: 3つの概念の関係と併用方法

このリポジトリでは以下の3つの仕組みを同時に使用しています。それぞれ**役割が完全に異なる**ため、互いに干渉しません。

### 3層モデル

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: Agent Skills & Custom Agents                          │
│           「誰が答えるか」= 専門家ペルソナ                          │
│   └─ .github/agents/*.md  (@メンションで呼び出し)                 │
│           例: @engineering-technical-writer / @engineering-code-reviewer │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: kiro SDD  (.kiro/specs/, kiro-*.prompt.md)            │
│           「どう開発するか」= 要件→設計→タスク→TDD のプロセス管理   │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Harness Engineering Docs  (AGENTS.md, docs/)          │
│           「何を作っているか」= プロジェクト知識ベース              │
└─────────────────────────────────────────────────────────────────┘
               ↑ すべてのレイヤーに常時適用 ↑
         .github/copilot-instructions.md (プロジェクトルール)
```

`copilot-instructions.md` は VS Code Copilot がどのエージェントモードでも**自動読み込み**します。どの Agent を使っていてもプロジェクトの禁止事項・規約は常に有効です。

---

### 概念 1: Harness Engineering Docs の追加方法

既存リポジトリに Harness スタイルのドキュメント構造を追加する手順です。

#### 必須ファイル

```
AGENTS.md                ← AI 向け目次（Quick Start + 鉄則 + ジャンプ先）
ARCHITECTURE.md          ← ASCII プロセス図 + ドメイン分解テーブル
docs/
├── DESIGN.md            ← 設計哲学・UI 規則
├── FRONTEND.md          ← スレッドモデル・UI パターン
├── PRODUCT_SENSE.md     ← ターゲットユーザー・価値提案
├── QUALITY_SCORE.md     ← 品質スコア・計測方法
├── RELIABILITY.md       ← 障害モード・信頼性設計
├── SECURITY.md          ← OWASP 対応・セキュリティ設計
├── design-docs/
│   ├── index.md         ← 設計書索引
│   ├── core-beliefs.md  ← 設計鉄則（変更してはいけない理由）
│   └── ...              ← ドメイン固有設計書
├── exec-plans/
│   ├── active/          ← 進行中タスク（フェーズ分解・受け入れ基準）
│   ├── completed/       ← 完了タスク（修正内容・検証結果）
│   └── tech-debt-tracker.md ← 技術的負債トラッカー
├── generated/           ← 自動生成ドキュメント（SHM レイアウト等）
└── product-specs/       ← プロダクト仕様・受け入れ基準
```

#### 作成の優先順位

1. **`AGENTS.md`** — 最初に作る。AI が最初に読むファイル
   - Quick Start（4ステップ）
   - コーディングの鉄則（違反 = PR 却下な5項目）
   - 頻出タスク別ジャンプ先テーブル
   - ファイル変更時チェックリスト
   - リポジトリ構造ツリー（`src/` 〜 `docs/` 全体）
   - 更新履歴テーブル

2. **`ARCHITECTURE.md`** — 2番目に作る
   - ASCII art プロセスマップ（3層: GUI / プロセス境界 / コア）
   - パッケージ階層（各ディレクトリの責務）
   - データフロー図
   - ドメイン分解テーブル（ドメイン | ファイル | 責務 | 制約）
   - 依存バージョンテーブル
   - セットアップ・ビルド手順

3. **`docs/design-docs/core-beliefs.md`** — 設計鉄則とその根拠
4. **`docs/exec-plans/`** — 進行中タスクを随時追加
5. **その他の `docs/` ファイル** — 必要なものから順次

#### AGENTS.md の必須セクション構成

```markdown
## 0. Quick Start（4ステップ）
## 0.1 コーディングの鉄則（違反 = PR 却下）
## 0.2 頻出タスク別ジャンプ先
## 0.3 ファイル変更時チェックリスト
## 0.4 更新履歴
## 1. プロジェクト概要
## 2. リポジトリ構造マップ（ツリー）
## 3. 重要ファイル早見表
## 4. 設計ドキュメント索引
## 5. 実行計画索引
## 6. コーディング規約サマリ（DO / DON'T）
## 7. テスト実行コマンド
```

---

### 概念 2: kiro SDD の追加方法

→ このガイドの Phase 0〜5 を参照してください（本文）。

**既存リポジトリへの追加の最小手順:**

```powershell
# 1. フレームワークインストール
npx cc-sdd@latest --copilot --lang ja

# 2. copilot-instructions.md を整備（技術スタック・禁止事項を記載）

# 3. 最初のフィーチャーから始める
# VS Code Copilot Chat で:
# /kiro-spec-init "次に開発する機能の説明"
```

**既存コードとの統合ポイント:**

| タイミング | 使うコマンド | 目的 |
|----------|------------|-----|
| 既存機能のドキュメント化 | `/kiro-validate-gap {feature}` | 「実装済み / 未実装」の棚卸し |
| 新機能開発開始時 | `/kiro-spec-init "説明"` | 仕様書を白紙から作成 |
| セッション終了時 | `docs/exec-plans/` と spec を手動更新 | 次回セッションへ進捗を引き継ぐ |
| 進捗確認時 | `/kiro-spec-status {feature}` | タスク完了率の確認 |

---

### 概念 3: Agent Skills の追加方法

Custom Agents は `.github/agents/*.md` の形式で定義された**専門家ペルソナ**です。Slash command 用の `.github/prompts/*.prompt.md` とは役割が異なります。

#### 含まれるエージェント

| ファイル名 | ペルソナ | 使いどころ |
|----------|--------|---------|
| `engineering-software-architect.md` | ソフトウェアアーキテクト | ドメイン設計・ADR・トレードオフ分析 |
| `engineering-omr-pipeline-engineer.md` | OMR パイプライン実装者 | Audiveris・画像前処理・品質ロジックの実装 |
| `engineering-code-reviewer.md` | コードレビュー担当 | Python 実装・型・テスト品質のレビュー |
| `engineering-technical-writer.md` | テクニカルライター | AGENTS / ARCHITECTURE / exec-plans の維持 |
| `testing-reality-checker.md` | 現実性チェッカー | release-ready 判定・証拠ベース検証 |

#### 使い方

VS Code Copilot Chat でエージェントを選択して使います：

```
# チャット入力欄でエージェント名を選択
# または @ でメンション

例: `@engineering-technical-writer AGENTS.md を現状に同期して`
例: `@engineering-software-architect musicxml-transform の設計をレビューして`
```

#### 独自エージェントの追加方法

`.github/agents/engineering-myagent.md` を作成：

```markdown
---
name: エージェント名
description: 一行説明（Copilot Chat の選択画面に表示される）
color: blue
emoji: 🛠️
vibe: 専門分野・判断基準・口調を 1〜3 行で記述
---

# エージェント名 パーソナリティ

あなたは**エージェント名**、〇〇を専門とするエキスパートです。

## コアミッション
- ミッション 1
- ミッション 2

## 制約
- このプロジェクト固有の制約（copilot-instructions.md と整合させる）
```

#### 重要: `copilot-instructions.md` との関係

Agent Skills がペルソナを変えても、`copilot-instructions.md` のルールは**常に上位**です。

```
Agent Skill        → 「どの視点で考えるか」を変える
copilot-instructions.md → 「何をしてはいけないか」は変えられない
```

例: ラピッドプロトタイパーエージェントでも、`import torch を Main Process で使う` という禁止事項は有効のまま。

---

### 3つの概念を組み合わせた開発フロー例

```
1. Agent Skill でアイデアを検討
   例: ラピッドプロトタイパーに「VAD バイパス機能の PoC 案を出して」

2. kiro SDD で仕様化
   /kiro-spec-init "VAD バイパス機能"
   /kiro-spec-requirements vad-bypass
   /kiro-spec-design vad-bypass
   /kiro-spec-tasks vad-bypass

3. Agent Skill + kiro-spec-impl で実装
   例: シニア開発者エージェントで「/kiro-spec-impl vad-bypass 1,2」

4. Harness docs への反映
   exec-plans/active/ に進捗を記録
   exec-plan と spec を更新してコンテキスト保存
```

---

*作成: 2026-03-12 | WarpVoiceChanger プロジェクトの実践から抽出*
