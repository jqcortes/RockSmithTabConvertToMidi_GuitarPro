# クイックリファレンス — cc-sdd コマンド

## インストール・実行

```bash
# 日本語テンプレートで SDD フレームワークを生成
npx cc-sdd@latest --copilot --lang ja
```

## 生成物

| ディレクトリ | ファイル数 | 内容 |
|---|---|---|
| `.github/prompts/` | 約11ファイル | kiro SDD コマンドプロンプト (`kiro-spec-init.prompt.md` 等) |
| `.kiro/settings/` | 約25ファイル | SDD テンプレート・ルール定義 |

## 注意事項

- **AGENTS.md が上書きされる**: cc-sdd はデフォルトテンプレートで AGENTS.md を上書きする。実行後に Harness Engineering スタイルへ手動更新が必要。
- Node.js v16+ が必要。
- インターネット接続が必要（npx がパッケージを取得）。

## kiro SDD コマンド一覧

| コマンド | 用途 | 生成先 |
|---|---|---|
| `/kiro-spec-init "説明"` | 新機能仕様の初期化 | `.kiro/specs/<feature>/` |
| `/kiro-spec-requirements {feature}` | 要件定義書生成 | `.kiro/specs/<feature>/requirements.md` |
| `/kiro-validate-gap {feature}` | コードとのギャップ分析 | 出力のみ |
| `/kiro-spec-design {feature}` | 設計書生成 | `.kiro/specs/<feature>/design.md` |
| `/kiro-spec-tasks {feature}` | タスク一覧生成 | `.kiro/specs/<feature>/tasks.md` |
| `/kiro-spec-impl {feature}` | TDD 実装 | 実装ファイル |
| `/kiro-spec-status {feature}` | 進捗確認 | 出力のみ |
| `/kiro-steering` | Steering ドキュメント更新 | `.kiro/steering/` |
| `/session-end` | セッション終了・コミット | git |

## SDD 3フェーズ承認フロー

```
/kiro-spec-requirements → [人間レビュー] → /kiro-spec-design → [人間レビュー] → /kiro-spec-tasks → [人間レビュー] → /kiro-spec-impl
```

各フェーズで承認なしに次フェーズへ進めないこと（`-y` フラグは意図的な高速化時のみ）。
