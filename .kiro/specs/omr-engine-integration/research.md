# Research & Design Decisions — omr-engine-integration

---
**Purpose**: Discover findings, architectural investigations, and rationale for omr-engine-integration design.

---

## Summary

- **Feature**: `omr-engine-integration`
- **Discovery Scope**: Complex Integration（外部 Java プロセス CLI ラッパー）
- **Key Findings**:
  - Audiveris CLI は `java -jar` 形式で呼び出し、終了コード 0 で成功判定する。出力は `{bookname}.mxl`（圧縮）または `{bookname}.xml`（非圧縮）の両形式が存在する
  - 既存コードベースの `image_loader.py` が確立したパターン（キャッシュ・`StepResult` ・`IngestError` ）をそのまま踏襲することで設計の一貫性を保てる
  - Audiveris の内部データモデル（Book/Sheet/SIG）は CLI 経由では直接触れられないため、出力 MusicXML の well-formed 検証に留める必要がある

---

## Research Log

### Audiveris CLI 仕様の確認

- **Context**: `docs/audiveris-cli-reference.md` および `docs/omr-pipeline.md` を精読
- **Sources Consulted**: `docs/audiveris-cli-reference.md`、`docs/omr-pipeline.md`
- **Findings**:
  - 基本構文: `java -jar audiveris.jar -batch -transcribe -export -output <dir> -- <input>`
  - Audiveris は `-option key=value` で追加 CLI オプションを受け取れるが、内部プロパティ変更は環境差分の影響が大きいため既定値に含めない方が安全
  - 出力は `.mxl`（圧縮 ZIP）または `.xml` が `output_dir/` 以下に生成される
  - 終了コード非0なら必ずエラー
  - `--` セパレータ後に入力ファイルを指定する形式
- **Implications**: subprocess で `java -jar <jar>` を呼ぶ際はシェル展開不要・リスト形式で渡すのが安全。追加 `-option` は `config/audiveris.properties` による明示設定時のみ注入する

### 既存パイプラインパターン分析

- **Context**: `pipeline/ingest/image_loader.py` および `pipeline/common.py` のコード精読
- **Sources Consulted**: ワークスペース内ソース
- **Findings**:
  - `load()` 関数が `StepResult.ok(output_path, metrics=…, warnings=…)` を返す単一エントリポイントパターンを確立
  - キャッシュは `cache_dir` 内の既存ファイル存在確認で判定（`Path.exists()`）
  - エラーは `IngestError(PipelineError)` を raise し呼び出し元で catch
  - ロガーは `get_logger(__name__)` でモジュール先頭に取得、`print()` 禁止
- **Implications**: `omr/` ドメインも `transcribe(image_path, output_dir) -> StepResult` の単一エントリ関数として設計する

### subprocess タイムアウト・セキュリティ要件

- **Context**: Audiveris は Java プロセスのため数分かかりうる
- **Findings**:
  - `subprocess.run(cmd, timeout=300, capture_output=True)` が標準パターン
  - `TimeoutExpired` 例外は `process.kill()` 後に `OmrError` へ変換
  - シェルインジェクション防止のため `shell=False`（リスト引数）を使う
  - `check=False` で終了コードを自前で判定する（CalledProcessError を catch せず直接比較）
- **Implications**: OWASP コマンドインジェクション防止のため `shell=False` + リスト引数が必須

### MusicXML 出力検証方法

- **Context**: Audiveris が出力する `.mxl` は ZIP 圧縮された MusicXML
- **Findings**:
  - `.mxl` は ZIP 内に `*.xml` を持つ形式（MusicXML Compressed format）
  - `lxml.etree.parse()` で well-formed かどうか確認できる（`.mxl` は一旦 `zipfile` で展開が必要）
  - `.xml`（非圧縮）は直接 `lxml.etree.parse()` で parse 可能
  - ファイル選択優先度: `.mxl` > `.xml`（圧縮版優先）
- **Implications**: `MusicXmlFinder` コンポーネントが glob で両形式を探し、lxml で well-formed を確認する

### 環境変数 vs 設定ファイルの優先度

- **Context**: CI・ローカル・本番で JAR パスが異なる
- **Findings**:
  - `AUDIVERIS_JAR` 環境変数 → 優先
  - `config/audiveris.properties` → フォールバック
  - プロパティファイルが存在しない場合はデフォルト値使用
  - `configparser` で `.properties` は `[DEFAULT]` セクションなしで読める（`python-dotenv` も可だが標準ライブラリ優先）
- **Implications**: `OmrConfig` クラスが env → props → default の優先度で設定を解決する

---

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| 単純関数（直接 subprocess） | `transcribe()` 内で全処理 | シンプル | テスト困難（subprocess モック複雑） | NG：テスタビリティが低い |
| Adapter パターン | `AudiverisRunner` クラスが CLI を wrap | テスト容易（クラスをモック化）・責務分離 | クラス数増加 | ✅ 採用 |
| プラグイン化 | OMR エンジンを抽象インターフェースで差し替え可能に | 将来の代替エンジン対応 | 過剰設計（今は Audiveris のみ） | NG：YAGNI 原則 |

---

## Design Decisions

### Decision: `AudiverisRunner` クラスによる CLI 抽象化

- **Context**: subprocess 直呼び出しだとテスト時に実際の Audiveris JAR が必要になる
- **Alternatives Considered**:
  1. モジュール関数の直接 subprocess — シンプルだがモック困難
  2. `AudiverisRunner` クラス — DI でモック可能
- **Selected Approach**: `AudiverisRunner` クラスを定義し、`transcribe()` 関数でデフォルトインスタンスを使用。テストは `AudiverisRunner` をモック化
- **Rationale**: `image_loader.py` が `pdf2image.convert_from_path` をモックターゲットとして明示 import するのと同じ発想
- **Trade-offs**: クラス数 +1 ／ テスタビリティ大幅向上
- **Follow-up**: pytest で `AudiverisRunner.run` を `@patch` でモック化するテストを用意する

### Decision: `.mxl` 優先・`.xml` フォールバック

- **Context**: Audiveris は Audiveris バージョンや設定で出力形式が異なる
- **Selected Approach**: `glob("*.mxl")` 優先、なければ `glob("*.xml")`
- **Rationale**: `.mxl` は圧縮済みで推奨形式だが、設定次第で非圧縮 XML が出る場合もある
- **Trade-offs**: コード +1 分岐 / 両形式対応で堅牢性向上

### Decision: `OmrError` 継承階層

- **Context**: OMR 固有エラーを `PipelineError` と区別しつつ型安全に扱いたい
- **Selected Approach**: `OmrError(PipelineError)` を基底に `OmrEnvironmentError`・`OmrTimeoutError`・`OmrExecutionError`・`OmrOutputError` を定義
- **Rationale**: 呼び出し元が `except OmrError` で一括 catch も `except OmrTimeoutError` で個別 catch もできる
- **Trade-offs**: クラス定義行数 +20 / 診断精度向上

---

## Risks & Mitigations

- **Java 未インストール環境への誤実行** — 環境検証を `transcribe()` 冒頭で実施し `OmrEnvironmentError` を raise することで即座に失敗させる
- **Audiveris の長時間実行** — `timeout=300` (設定可変) でプロセスを強制終了し `OmrTimeoutError` を raise する
- **MXL 圧縮形式の parse 失敗** — `.mxl` 展開エラーは `OmrOutputError` にラップし、`.xml` フォールバックを試みる
- **並行実行時の出力ディレクトリ競合** — `output_dir` を呼び出し元が一意なパスで渡すことを API 契約に明記（本ドメインは管理しない）

---

## References

- [Audiveris 公式ドキュメント](https://audiveris.github.io/audiveris/) — CLI オプション・出力形式
- `docs/audiveris-cli-reference.md` — プロジェクト内 CLI リファレンス（Audiveris 5.3 準拠）
- `docs/omr-pipeline.md` — OMR パイプライン詳細・チューニング方針
- `pipeline/ingest/image_loader.py` — キャッシュ・StepResult パターンの参照実装
- `pipeline/common.py` — PipelineError 階層・structlog 設定
