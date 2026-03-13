# Project Structure

## Organization Philosophy

ドメイン駆動設計。`pipeline/` 配下に 5 つのドメインを配置し、各ドメインは独立したモジュールとして実装する。
ドメイン間はファイルパス文字列のみで通信し、直接 import しない。

## Directory Patterns

### pipeline/ — パイプライン実装コア
**Location**: `/pipeline/`  
**Purpose**: 入力〜出力までの 5 ドメインを格納する  
**Domains**:
- `ingest/` — PDF/PNG → 前処理済み 300dpi PNG（✅ 実装済み）
- `omr/` — Audiveris CLI ラッパー → MusicXML（✅ 実装済み）
- `transform/` — MusicXML バリデーション・ギター補正・パート分離・quality gate（✅ 実装済み）
- `render/` — MusicXML → MIDI Type 1（✅ 実装済み）
- `quality/` — 品質スコア計算・レポート生成（✅ 実装済み）

**CLI パターン** (`pipeline/__main__.py`):
- `convert` — `load → preprocess → validate → transcribe → transform → render → score` を配線
- `quality` — 既存 MusicXML / MIDI を再評価
- 終了コード: `PASS=0`, `REVIEW=1`, `FAIL=2`, 入力/パイプラインエラー=`3`, OMR エラー=`4`

**OMR ドメインの内部構成パターン** (`pipeline/omr/` を参照):
- `__init__.py` — 公開 API のみ re-export（例: `from pipeline.omr._transcribe import transcribe`）
- `_transcribe.py` — ドメインのエントリポイント関数（設定→検証→キャッシュ→実行→探索の順）
- `errors.py` — ドメイン固有例外階層（`PipelineError` → `OmrError` → 4サブクラス）
- `config.py` — 設定ロード（env var → properties ファイル → デフォルト値の優先順）
- `engine.py` — 外部ツール環境検証（Java バージョン・JAR 存在確認）
- `runner.py` — CLI 実行ラッパー（subprocess + タイムアウト管理）
- `finder.py` — 出力ファイル探索・well-formed 検証

### tests/ — テストコード
**Location**: `/tests/`  
**Purpose**: ユニットテスト・統合テスト・フィクスチャ  
**Example**:
- `tests/unit/test_omr/` — OMR ドメインのユニットテスト群（サブディレクトリ方式）
- `tests/unit/test_common.py` — 共通型・例外のテスト
- `tests/integration/test_cli_integration.py` — CLI の Transform → Render → Quality 連携テスト
- `tests/fixtures/` — Ingest 用 PDF/PNG と Transform / Render / Quality 用 MusicXML フィクスチャ

**テストディレクトリパターン**: ドメインのサブモジュールが多い場合は `tests/unit/test_<domain>/` ディレクトリを作成し `__init__.py` を配置する

### config/ — 設定ファイル
**Location**: `/config/`  
**Purpose**: Audiveris 設定・楽器マップ・パイプライン設定  
**Status**: `instrument_map.yaml` は存在。`audiveris.properties`, `pipeline.yaml` は今後追加余地あり

### docs/ — ドキュメント
**Location**: `/docs/`  
**Purpose**: 設計書・仕様書・CLI リファレンス  
**Key files**:
- `docs/DESIGN.md` — 詳細設計書
- `docs/FRONTEND.md` — CLI インターフェース仕様 (サブコマンド・オプション・終了コード定義)
- `docs/design-docs/core-beliefs.md` — 設計鉄則 (変更には要レビュー)
- `docs/exec-plans/` — 進行中・完了タスクの実行計画

### tmp/ — 一時ファイル
**Location**: `/tmp/`  
**Purpose**: 中間成果物の一時保存 (`.gitignore` 対象)  
**Rule**: `pipeline/` 配下に一時ファイルを永続化しない

## Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Test files**: `test_<module_name>.py`
- **Config files**: `snake_case.yaml` / `snake_case.properties`

## Import Organization

```python
# 標準ライブラリ
import subprocess
from pathlib import Path

# サードパーティ
import structlog
from music21 import converter

# プロジェクト内 (ドメイン間 import は StepResult 経由で)
from pipeline.common import StepResult, PipelineError
```

**重要規則**:
- ドメイン間の直接 import を避ける (例: `render/` から `omr/` を import しない)
- `pipeline/` から `tests/` を import しない
- `Main Process` で `import torch` を使わない

## Code Organization Principles

- 各ドメインモジュールは `StepResult` を返す単一エントリ関数を持つ
- エラーは `PipelineError` を継承した例外で伝播し、呼び出し元でキャッチする
- 各ドメインの出力はディスクにキャッシュし、`output_path` を `StepResult` に含める

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_
