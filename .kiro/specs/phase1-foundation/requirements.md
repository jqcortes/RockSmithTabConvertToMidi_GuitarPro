# Requirements Document

## Introduction

`phase1-foundation` は band-score-to-midi パイプラインの共通基盤と Ingest ドメインを実装する。
パイプライン全ドメインで共有される `StepResult` / `PipelineError` 型を定義し、
PDF/PNG のバンドスコア画像を Audiveris が処理可能な高品質 PNG (300dpi+) に変換する Ingest ドメイン3モジュール
（`ImageLoader`, `Preprocessor`, `InputValidator`）を TDD で実装する。

参照: `docs/phase1-foundation.md` / `docs/DESIGN.md` § Phase 1

---

## Requirements

### Requirement 1: 共通パイプライン型定義

**Objective:** パイプライン開発者として、全ドメインで一貫したデータ転送型とエラー処理を利用したい。ドメイン間の結合を疎に保ちながら結果・エラーを統一的に扱えるようにするため。

#### Acceptance Criteria

1. The Ingest Module shall define `StepResult(success: bool, output_path: Path | list[Path], metrics: dict[str, MetricValue], warnings: list[str])` as a dataclass in `pipeline/common.py`, where `MetricValue = float | int | str | bool | list[str] | dict[str, str]` is the shared metrics contract for all pipeline domains.
2. The Ingest Module shall define `PipelineError` as a base exception class in `pipeline/common.py`.
3. When a domain step fails, the Ingest Module shall raise an exception that inherits from `PipelineError`.
4. The Ingest Module shall annotate all public functions and class signatures with type hints compatible with `mypy --strict`.
5. The Ingest Module shall not use `print()` in pipeline code; all logging shall use `structlog` with structured JSON output.

---

### Requirement 2: PDF / 画像ファイル読み込み (ImageLoader)

**Objective:** パイプライン利用者として、PDF・PNG・TIFF・JPEG などの入力形式を統一的なインターフェースで読み込みたい。形式差異を意識せずに前処理ステップへ渡せるようにするため。

#### Acceptance Criteria

1. When a PDF file is provided as input, the Ingest Module shall convert each page to PNG at 300dpi using `pdf2image`.
2. When a PNG, TIFF, or JPEG file is provided as input, the Ingest Module shall load it directly without re-encoding to lossy formats.
3. If the input file does not exist, the Ingest Module shall raise `IngestError` (inherits `PipelineError`) with the file path in the message.
4. If the input file format is unsupported, the Ingest Module shall raise `IngestError` with a list of supported formats.
5. The Ingest Module shall return a `StepResult` containing the list of output PNG paths in `output_path`.
6. The Ingest Module shall cache output PNG files to disk so that re-runs skip re-conversion when the source file is unchanged.

---

### Requirement 3: 画像前処理 (Preprocessor)

**Objective:** OMR エンジニアとして、Audiveris の認識精度を最大化するために楽譜画像を標準化された形式に前処理したい。傾き・ノイズ・コントラストの問題を自動補正することで人手介入ゼロを実現するため。

#### Acceptance Criteria

1. When an image with skew angle within ±10 degrees is provided, the Ingest Module shall deskew it using Hough transform and return the corrected image.
2. The Ingest Module shall convert input images to grayscale before applying subsequent preprocessing steps.
3. The Ingest Module shall apply Otsu thresholding to produce a binary image.
4. The Ingest Module shall apply CLAHE (Contrast Limited Adaptive Histogram Equalization) for contrast normalization.
5. The Ingest Module shall trim page margins by auto-cropping to the detected score region.
6. The Ingest Module shall return a `StepResult` with the preprocessed PNG path and preprocessing metrics (skew angle, binarization threshold) in `metrics`.
7. If any preprocessing step produces an output where black pixel ratio is outside 5–40%, the Ingest Module shall add a warning to `StepResult.warnings`.

---

### Requirement 4: 入力品質検証 (InputValidator)

**Objective:** パイプライン利用者として、処理不可能な低品質画像を早期に検出したい。下流の OMR 処理で無駄な時間を消費しないようにするため。

#### Acceptance Criteria

1. When image resolution is below 200dpi, the Ingest Module shall raise `IngestError` with the message indicating the minimum required resolution.
2. When image resolution is between 200dpi and 299dpi, the Ingest Module shall add a resolution warning to `StepResult.warnings` and continue processing.
3. When image resolution is 300dpi or above, the Ingest Module shall proceed without warnings related to resolution.
4. If the black pixel ratio of the binarized image is outside the range of 5–40%, the Ingest Module shall add a quality warning to `StepResult.warnings`.
5. The Ingest Module shall expose a single entry-point function `validate(image_path: Path) -> StepResult` that performs all validation checks.

---

### Requirement 5: ユニットテストとフィクスチャ

**Objective:** 開発者として、各モジュールが仕様通りに動作することを自動的に検証したい。リグレッションを防ぎながら安全にリファクタリングできるようにするため。

#### Acceptance Criteria

1. The Ingest Module shall have unit tests in `tests/unit/test_ingest.py` covering all public functions of `ImageLoader`, `Preprocessor`, and `InputValidator`.
2. The Ingest Module shall include test fixtures in `tests/fixtures/` containing at minimum one sample PDF and one sample PNG of a guitar score.
3. When running `python -m pytest tests/unit/ -v`, all unit tests shall pass with exit code 0.
4. The Ingest Module shall achieve a test line coverage of 80% or above for `pipeline/ingest/` as measured by `pytest-cov`.
5. The Ingest Module shall not require a live Audiveris installation or Java runtime for unit tests to pass.

