---
# .kiro/steering/product.md テンプレート
# AI がリポジトリの目的・ユーザー・スコープを把握するための永続メモリ
---

# プロダクト概要

## 目的

{{PROJECT_NAME}} は {{TARGET_USER}} のための {{CORE_PROBLEM_DESCRIPTION}} を解決するツールです。

## ターゲットユーザー

- {{USER_TYPE_1}}（例: ギタリスト個人ユーザー）
- {{USER_TYPE_2}}（例: DTM 制作者）

## 主要ユースケース

1. **{{USE_CASE_1}}**: {{UC1_DESCRIPTION}}
2. **{{USE_CASE_2}}**: {{UC2_DESCRIPTION}}
3. **{{USE_CASE_3}}**: {{UC3_DESCRIPTION}}

## スコープ外

- {{OUT_OF_SCOPE_1}}（例: リアルタイム処理）
- {{OUT_OF_SCOPE_2}}（例: クラウドサービス）
- {{OUT_OF_SCOPE_3}}

## 成功の定義

- {{SUCCESS_METRIC_1}}（例: 変換精度 80% 以上）
- {{SUCCESS_METRIC_2}}（例: 処理時間 5 分以内）

---
# .kiro/steering/tech.md テンプレート
# 技術スタック・コーディング規約・重要な技術決定
---

# 技術スタック

## コア技術

| 層 | 技術 | バージョン | 選定理由 |
|---|---|---|---|
| 言語 | {{LANGUAGE}} | {{VERSION}} | {{REASON}} |
| {{LAYER_2}} | {{TECH_2}} | {{VER_2}} | {{REASON_2}} |

## コーディング規約

### 型システム
- すべての公開 API に型ヒントを付ける
- `TypedDict` / `dataclass` でデータ転送型を定義する

### エラー処理
- `{{BASE_ERROR}}` を基底クラスとして使う
- 外部 I/O は必ずタイムアウト付きでラップする

### テスト
- ユニットテスト: `tests/unit/`
- 統合テスト: `tests/integration/`
- フィクスチャ: `tests/fixtures/`
- カバレッジ目標: {{COVERAGE_TARGET}}%

## 重要な技術決定

| 決定 | 選択肢 | 採用 | 理由 |
|---|---|---|---|
| {{DECISION_1}} | {{OPTIONS_1}} | {{CHOICE_1}} | {{REASON_1}} |

## パフォーマンス要件

- {{PERF_REQ_1}}（例: OMR 処理は 5 分以内）
- {{PERF_REQ_2}}

---
# .kiro/steering/structure.md テンプレート
# ディレクトリ構造・命名規則・ファイル配置ルール
---

# プロジェクト構造

## ディレクトリ構造

```
{{PROJECT_ROOT}}/
├── {{PRIMARY_CODE_DIR}}/    # コアロジック
│   ├── {{DOMAIN_1}}/        # {{DOMAIN_1_DESC}}
│   ├── {{DOMAIN_2}}/        # {{DOMAIN_2_DESC}}
│   └── {{DOMAIN_3}}/        # {{DOMAIN_3_DESC}}
├── tests/
├── config/
└── docs/
```

## 命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| ファイル | `snake_case.{{EXT}}` | `guitar_fixer.py` |
| クラス | `PascalCase` | `GuitarFixer` |
| 関数 | `snake_case` | `process_tab()` |
| 定数 | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |

## ファイル配置ルール

- 一時ファイル: `tmp/` 以下（`{{PRIMARY_CODE_DIR}}/` に永続化しない）
- 設定ファイル: `config/` 以下
- テストデータ: `tests/fixtures/` 以下

## ドメイン境界

各ドメインは `StepResult(success, output_path, metrics, warnings)` を返す。
ドメイン間はファイルパス文字列で疎結合にする（直接 import 禁止）。
