# Technology Stack

## Architecture

ドメイン駆動のパイプライン設計。各ドメインはファイルパス文字列で疎結合し、`StepResult` を返す。

```
Ingest → OMR (Audiveris CLI) → Transform → Render → Quality
```

## Core Technologies

- **Language**: Python 3.11+
- **OMR Engine**: Audiveris 5.3+ (Java 17+ 必須、CLI 経由のみ使用)
- **Runtime**: ローカル CLI / バッチ処理

## Key Libraries

| ライブラリ | バージョン | 用途 |
|---|---|---|
| music21 | 9.x | MusicXML パース・MIDI 生成 |
| opencv-python | 4.x | 画像前処理 (デスキュー・二値化) |
| pillow | 10.x | 画像 I/O |
| pdf2image | 1.x | PDF → PNG 変換 (poppler 依存) |
| lxml | 4.x | MusicXML XML パース |
| mido | 1.x | 低レベル MIDI 操作 |
| structlog | 任意 | 構造化 JSON ログ |

## Development Standards

### Type Safety
- すべての公開関数・クラスに型ヒントを付ける（`mypy strict` 相当）
- `Any` 型の使用は最小限に

### Code Quality
- ファイル名: `snake_case.py`、クラス名: `PascalCase`、定数: `UPPER_SNAKE_CASE`
- パイプラインコードで `print()` を使わない（`structlog` を使う）

### Testing
- `tests/unit/` にユニットテスト、`tests/integration/` に統合テスト
- TDD 推奨: テストを先に書いてから実装する
- テストフィクスチャは `tests/fixtures/` に格納

## Development Environment

### Required Tools
- Python 3.11+
- Java 17+ (Audiveris 実行用)
- Audiveris 5.3+ JAR

### Common Commands
```bash
# ユニットテスト
python -m pytest tests/unit/ -v

# OMR ドメインのテスト（カバレッジ付き）
python -m pytest tests/unit/test_omr/ --cov=pipeline/omr --cov-report=term-missing

# 統合テスト
python -m pytest tests/integration/

# 型チェック
python -m mypy pipeline/ --strict

# パイプライン実行
python -m pipeline.main --input path/to/score.pdf --output out/
```

## Key Technical Decisions

1. **CLI 経由のみで Audiveris を呼ぶ**: Java 内部クラスへの直接依存を排除し、バージョンアップ耐性を確保
2. **ドメイン間をファイルパスで疎結合**: 各ドメインは `StepResult(success, output_path, metrics, warnings)` を返す
3. **タブ譜優先**: ギター TAB のフレット情報を五線譜より優先するロジックを `guitar_fixer.py` に集約
4. **subprocess タイムアウト必須**: Audiveris CLI 呼び出しは `Popen` + `communicate(timeout=N)` パターンを使用。タイムアウト時は `proc.kill()` → `OmrTimeoutError` へ変換
5. **設定優先順**: `AUDIVERIS_JAR` 環境変数 → `config/audiveris.properties` → デフォルト値。`configparser` は `optionxform = str` でキーの大文字を保持する
6. **キャッシュ-ファースト実行**: `MusicXmlFinder.find()` を先行試行し、`OmrOutputError` 時のみ CLI を起動する

---
_Document standards and patterns, not every dependency_
