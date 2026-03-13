# GitHub Copilot 指示書 — band-score-to-midi

> このファイルは VS Code Copilot が全セッションで自動読み込みします。
> すべての Agent / Spec に共通して適用されるプロジェクトルールです。

---

## プロジェクト概要

バンドスコア（ギター楽譜、スキャン PDF/PNG）を MIDI ファイルに自動変換するパイプライン。
Audiveris OMR エンジンを CLI 経由で呼び出し、MusicXML を経由して MIDI Type 1 を生成する。
ターゲット: ギタリスト個人ユーザー・DTM 制作者向けのローカル CLI ツール。

詳細: `ARCHITECTURE.md` / `docs/design-docs/core-beliefs.md`

---

## 技術スタック

| 層 | 技術 | バージョン |
|---|---|---|
| 言語 | Python | 3.11+ |
| OMR エンジン | Audiveris | 5.3+ (要 Java 17+) |
| MusicXML / MIDI 操作 | music21 | 9.x |
| 画像前処理 | opencv-python | 4.x |
| 画像 I/O | pillow | 10.x |
| XML パース | lxml | 4.x |
| 低レベル MIDI | mido | 1.x |
| 構造化ログ | structlog | 任意 |

---

## アーキテクチャ ドメイン

```
入力 (Ingest) → OMR (Audiveris CLI) → 変換 (Transform) → 出力 (Render) → 品質 (Quality)
    image_in/        omr_engine/          xml_processor/     midi_out/       scorer/
```

- **Ingest**: PDF/PNG → 前処理済み 300dpi PNG
- **OMR**: Audiveris CLI -batch -transcribe -export → MusicXML
- **Transform**: MusicXML バリデーション / ギター補正 / パート分離
- **Render**: MusicXML → MIDI Type 1 (per-channel, tempo/instrument 付き)
- **Quality**: 品質スコア計算 → quality_report.json

---

## 設計の鉄則（違反 = PR 却下）

1. **タブ譜優先**: 五線譜とタブ譜が共存する場合は必ずタブ譜のフレット情報を pitch の正解とする
2. **信頼度に正直に**: 信頼度が閾値未満のノートは MIDI に含めず警告レポートに記録する（無理に出力しない）
3. **エンジン内部に触れない**: Audiveris パラメータ変更は最終手段。前後の処理層で品質を確保する
4. **ステップキャッシュ必須**: 各ステップは出力をディスクにキャッシュし、特定ステップからの再実行を可能にする
5. **ドメイン間はファイルパス文字列で疎結合**: 各ドメインは `StepResult(success, output_path, metrics, warnings)` を返す

---

## コーディング規約

### 型・命名
- すべての公開関数・クラスに型ヒントを付ける
- ファイル名: `snake_case.py`
- クラス名: `PascalCase`
- 定数: `UPPER_SNAKE_CASE`

### エラー処理
- パイプラインエラーは `PipelineError` を継承した例外で伝播する
- 外部 API (Audiveris CLI) の呼び出しは subprocess タイムアウトを必ず設定する

### ログ
- `structlog` で構造化 JSON ログを出力する
- プレーンな `print()` をパイプラインコードで使わない（デバッグ用一時使用は可）

### テスト
- `tests/unit/` にユニットテスト、`tests/integration/` に統合テストを置く
- テストフィクスチャは `tests/fixtures/` に格納する
- TDD 推奨: テストを先に書いてから実装する

---

## 禁止事項

- `Main Process` (CLI エントリポイント) で `import torch` を使わない（重量モデルの直接ロード禁止）
- Audiveris のソースコードや内部 Java クラスを直接呼び出さない（CLI のみ使用）
- `quality_score < 0.5` のノートを MIDI に含めない
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
| `/kiro-validate-design {feature}` | 設計レビューと実装準備確認 |
| `/kiro-spec-tasks {feature}` | タスク一覧を生成 |
| `/kiro-spec-impl {feature} [tasks]` | TDD 実装 |
| `/kiro-validate-impl {feature}` | 実装の要件充足を確認 |
| `/kiro-spec-status {feature}` | 進捗確認 |
| `/kiro-steering` | Steering ドキュメントを生成・更新 |

Specs は `.kiro/specs/` に、Steering は `.kiro/steering/` に保存される。

`/kiro-spec-impl` を使う前に、対象 spec の `spec.json` で `approvals.tasks.approved` が `true` になっていることを確認すること。

このリポジトリには現時点で `/session-end` prompt は導入されていない。セッション終了時は `docs/exec-plans/` と必要な `.kiro/specs/*/spec.json` を手動で更新する。

---

## Agent Skills（専門家エージェント）

`.github/agents/` に登録済みのエージェントを Copilot Chat で `@エージェント名` として呼び出せます。

| エージェント | ファイル | 使いどころ |
|---|---|---|
| 🏛️ Software Architect | `engineering-software-architect.md` | ドメイン境界設計・ADR 作成・トレードオフ分析 |
| 🤖 OMR Pipeline Engineer | `engineering-omr-pipeline-engineer.md` | Audiveris 連携・画像前処理・品質スコアリング実装 |
| 👁️ Code Reviewer | `engineering-code-reviewer.md` | Python コードレビュー・型ヒント・PipelineError 確認 |
| 📚 Technical Writer | `engineering-technical-writer.md` | ドキュメント更新・AGENTS.md 維持・exec-plans 管理 |
| 🧐 Reality Checker | `testing-reality-checker.md` | 実装の証拠ベース品質検証・リリース可否判定 |

---

## 重要ドキュメント

| ファイル | 内容 |
|---|---|
| `AGENTS.md` | AI 向け目次・Quick Start |
| `ARCHITECTURE.md` | システム図・ドメイン分解 |
| `docs/design-docs/core-beliefs.md` | 設計鉄則とその根拠 |
| `docs/DESIGN.md` | 詳細設計書 |
| `docs/FRONTEND.md` | CLI インターフェース仕様 |
| `docs/QUALITY_SCORE.md` | 品質スコア定義 |
| `docs/audiveris-cli-reference.md` | Audiveris CLI リファレンス |
| `docs/guitar-specific.md` | ギター特有処理の仕様 |
| `.github/skills/sdd-repo-setup/SKILL.md` | SDD リポジトリセットアップ・更新スキル |
