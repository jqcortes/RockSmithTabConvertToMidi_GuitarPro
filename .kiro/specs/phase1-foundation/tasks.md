# Implementation Plan — phase1-foundation

## Task Format

- `(P)` = 並列実行可能タスク
- `*` = オプション（MVP 後に対応可）

---

## Tasks

- [x] 1. 共通パイプライン型を定義する
  - `pipeline/` ディレクトリと `pipeline/__init__.py` を作成する
  - `pipeline/common.py` に `StepResult` dataclass を定義する（`success`, `output_path`, `metrics`, `warnings` の各フィールドと `StepResult.ok()` ファクトリメソッド）
  - `pipeline/common.py` に `PipelineError` 基底例外クラスと `IngestError` サブクラスを定義する
  - すべてのシンボルに型ヒントを付け `mypy --strict` が通ることを確認する
  - `structlog` を使った構造化 JSON ロガーを `common.py` に初期設定する（`print()` 使用禁止）
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. PDF・画像ファイルを PNG に読み込む機能を実装する
  - `pipeline/ingest/` ディレクトリと `__init__.py` を作成する
  - PDF ファイルを `pdf2image` (dpi=300) で各ページ PNG に変換しキャッシュディレクトリに保存する機能を実装する
  - PNG / TIFF / JPEG ファイルをキャッシュディレクトリへコピーし、既存ファイルがある場合はスキップする機能を実装する
  - 非対応拡張子・ファイル不在の場合に `IngestError` を raise する
  - キャッシュヒット時は再変換をスキップし `StepResult.metrics["cached"] = True` を返す
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 3. 画像前処理（デスキュー・二値化・CLAHE）を実装する
  - 入力 PNG をグレースケールに変換する処理を実装する
  - `HoughLinesP` でスタッフラインの傾きを検出し ±10° 以内なら回転補正する（超過時は `warnings` に追記して補正スキップ）
  - Otsu 二値化を適用する
  - CLAHE (clipLimit=2.0, tileGridSize=8×8) でコントラスト正規化を適用する
  - 楽譜領域の外接矩形を検出して余白をトリミングする
  - 処理後に黒画素比率を算出し 5〜40% 範囲外なら `StepResult.warnings` に追記する
  - `StepResult.metrics` に `skew_angle`, `binarization_threshold`, `black_pixel_ratio` を含める
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 4. 入力画像の解像度・品質を検証する機能を実装する
  - PIL で画像の DPI 情報を取得し解像度を判定する機能を実装する
  - 解像度 < 200dpi の場合に `IngestError` を raise する
  - 200dpi 以上 300dpi 未満の場合に `StepResult.warnings` に低解像度警告を追加する
  - 黒画素比率が 5〜40% 範囲外の場合に `StepResult.warnings` に品質警告を追加する
  - `validate(image_path)` という単一エントリポイント関数として公開し `StepResult` を返す
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 5. ユニットテストとフィクスチャを整備する
- [x] 5.1 (P) テスト用フィクスチャを作成する
  - `tests/fixtures/` ディレクトリを作成する
  - ギター楽譜のサンプル PDF（最低1ページ）を配置する
  - サンプル PNG（300dpi 相当）を配置する
  - _Requirements: 5.2_
- [x] 5.2 (P) `pipeline/common.py` のユニットテストを書く
  - `StepResult` dataclass の各フィールドと `ok()` ファクトリメソッドをテストする
  - `PipelineError` / `IngestError` の継承関係をテストする
  - `mypy --strict` が通ることを確認するテストを追加する
  - _Requirements: 5.1, 5.3_
- [x] 5.3 `ImageLoader` のユニットテストを書く
  - `pdf2image.convert_from_path` をモック化して PDF 変換ロジックをテストする（Java/poppler 不要）
  - PNG / TIFF / JPEG の読み込みをテストする
  - キャッシュヒット / ミスをテストする
  - `IngestError` が正しく raise されることをテストする
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 5.1, 5.3, 5.5_
- [x] 5.4 `Preprocessor` のユニットテストを書く
  - デスキュー（±10° 以内・超過のケース両方）をテストする
  - Otsu 二値化・CLAHE・余白トリミングの適用をテストする
  - 黒画素比率警告が正しく `StepResult.warnings` に入ることをテストする
  - `StepResult.metrics` の各キーが含まれることをテストする
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 5.1, 5.3_
- [x] 5.5 `InputValidator` のユニットテストを書く
  - 解像度ゲート（200dpi 未満・200〜300dpi・300dpi 以上）の境界値をテストする
  - 黒画素比率の範囲外・範囲内をテストする
  - `validate()` が `StepResult` を返すことをテストする
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.3_
- [x]* 5.6 カバレッジ計測を設定し 80% 以上を確認する
  - `pytest --cov=pipeline/ingest --cov-report=term-missing` でカバレッジを計測する
  - 80% を下回るモジュールを特定し不足テストを追加する
  - _Requirements: 5.4_
