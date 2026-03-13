# Implementation Plan — quality-scoring

## Task Overview

| # | タスク | 並列 | 要件カバレッジ |
|---|---|---|---|
| 1 | Quality 例外階層を実装する | — | 4.1 |
| 2 | 入力検証を実装する | — | 5.1-5.4 |
| 3 | 品質メトリクス計算を実装する | P | 1.1-1.5 |
| 4 | 総合スコア判定を実装する | P | 2.1-2.5 |
| 5 | JSON レポート生成を実装する | P | 3.1-3.4 |
| 6 | エントリポイントとキャッシュを実装する | — | 4.2-4.5 |
| 7 | フィクスチャとユニットテストを整備する | — | 全要件 |

---

## Tasks

- [x] 1. Quality ドメインの例外階層を実装する
- [x] 1.1 `QualityError`、`QualityValidationError`、`QualityExecutionError` を定義する
  - `PipelineError` 継承の基底 / サブクラスを実装する
  - 対応ユニットテストを書く
  - _Requirements: 4.1_

- [x] 2. 入力検証を実装する
- [x] 2.1 `QualityInputValidator` を実装する
  - MusicXML と MIDI の存在確認を行う
  - MusicXML パース失敗、MIDI 読み込み失敗を `QualityValidationError` に変換する
  - _Requirements: 5.1, 5.2_

- [x] 3. (P) 品質メトリクス計算を実装する
- [x] 3.1 `QualityMetricsCalculator` を実装する
  - `omr_confidence` を算出する
  - `measure_completeness` を算出する
  - `pitch_range_validity` を算出する
  - `part_detection_rate` を算出する
  - warnings / total_measures / total_notes を返す
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 4. (P) 総合スコア判定を実装する
- [x] 4.1 `QualityJudge` を実装する
  - 重み付き総合スコアを算出する
  - PASS / REVIEW / FAIL を返す
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5. (P) JSON レポート生成を実装する
- [x] 5.1 `QualityReporter` を実装する
  - `quality_report.json` を出力する
  - `metrics`, `warnings`, `stats` を JSON に整形する
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 6. エントリポイントとキャッシュを実装する
- [x] 6.1 `score(musicxml_path, midi_path, output_dir) -> StepResult` を実装する
  - `quality_report.json` のキャッシュヒットを先に確認する
  - validator / metrics / judge / reporter を統合する
  - `pipeline/quality/__init__.py` から re-export する
  - `print()` を使わず `structlog` を用いる
  - _Requirements: 4.2, 4.3, 4.4, 4.5_

- [x] 7. フィクスチャとユニットテストを整備する
- [x] 7.1 Quality 用 fixture を追加する
  - 良好ケース / 小節不整合ケース / 音域外ノートケースを追加する
  - _Requirements: 1.2, 1.3, 3.3_
- [x] 7.2 ユニットテストと検証を追加する
  - `tests/unit/test_quality/` を作成する
  - `pytest --cov=pipeline/quality --cov-report=term-missing` でカバレッジ 95%+ を確認する
  - `python -m mypy pipeline/quality --strict` を通す
  - _Requirements: 全要件_