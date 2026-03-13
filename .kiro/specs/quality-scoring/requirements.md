# Requirements Document

## Introduction

`quality-scoring` は、Render ドメインが出力した MIDI と Transform 済み MusicXML を対象に、
品質スコアを算出し、判定結果と警告詳細を `quality_report.json` として出力する Quality ドメインである。

主な責務は次の 5 点:
1. 品質メトリクスの算出
2. 総合品質スコアの計算
3. PASS / REVIEW / FAIL 判定
4. JSON 品質レポート出力
5. `StepResult` 返却・キャッシュ・例外階層の提供

---

## Requirements

### Requirement 1: 個別品質メトリクスを算出する

**Objective:** パイプラインエンジニアとして、最終結果の品質を構成する各メトリクスを個別に観測したい。

#### Acceptance Criteria

1. The Quality Service shall `omr_confidence` を 0.0 〜 1.0 の範囲で算出する。
2. The Quality Service shall `measure_completeness` を各小節の音価整合性から 0.0 〜 1.0 で算出する。
3. The Quality Service shall `pitch_range_validity` をギター / ベースの妥当音域判定から 0.0 〜 1.0 で算出する。
4. The Quality Service shall `part_detection_rate` を期待パートに対する検出率として 0.0 〜 1.0 で算出する。
5. The Quality Service shall 各メトリクスを `StepResult.metrics` と品質レポート `metrics` の両方に含める。

---

### Requirement 2: 総合品質スコアと判定を決定する

**Objective:** CLI 利用者として、結果がそのまま使えるか、確認が必要か、失敗かを自動判定したい。

#### Acceptance Criteria

1. The Quality Service shall `overall_score = 0.40 * omr_confidence + 0.30 * measure_completeness + 0.15 * pitch_range_validity + 0.15 * part_detection_rate` を用いて総合スコアを算出する。
2. When `overall_score >= 0.80` のとき, the Quality Service shall `judgment = "PASS"` を返す。
3. When `0.60 <= overall_score < 0.80` のとき, the Quality Service shall `judgment = "REVIEW"` を返す。
4. When `overall_score < 0.60` のとき, the Quality Service shall `judgment = "FAIL"` を返す。
5. The Quality Service shall 総合スコアと判定を `StepResult.metrics` と品質レポートに記録する。

---

### Requirement 3: 警告と統計を JSON レポートへ出力する

**Objective:** DTM 制作者として、どこが怪しいかを後から確認できる JSON レポートが欲しい。

#### Acceptance Criteria

1. The Quality Service shall `quality_report.json` を `output_dir` に出力する。
2. The Quality Service shall レポートに `input_file`, `output_midi`, `timestamp`, `overall_score`, `judgment`, `metrics`, `warnings`, `stats` を含める。
3. When 小節完全性エラーや音域外ノートが検出されたとき, the Quality Service shall `warnings` に location と detail を含む辞書を記録する。
4. The Quality Service shall `stats` に `total_measures`, `total_notes`, `processing_time_seconds` を含める。

---

### Requirement 4: キャッシュ・公開 API・例外階層を提供する

**Objective:** パイプラインエンジニアとして、Quality ステップも他ドメインと同様に再実行制御と型安全な障害処理を持たせたい。

#### Acceptance Criteria

1. The Quality Service shall `PipelineError` を継承した `QualityError` 基底クラスを持ち、少なくとも `QualityValidationError` と `QualityExecutionError` を提供する。
2. When `output_dir/quality_report.json` が既に存在するとき, the Quality Service shall キャッシュヒットとして再計算をスキップし、`StepResult.metrics["cached"] = True` を返す。
3. The Quality Service shall 公開エントリポイント関数 `score(musicxml_path: Path, midi_path: Path, output_dir: Path) -> StepResult` を `pipeline/quality/__init__.py` から re-export する。
4. The Quality Service shall すべての公開関数・クラスに型ヒントを付け、`mypy --strict` 相当で通る実装とする。
5. The Quality Service shall `print()` を使用せず、`structlog` で診断ログを出力する。

---

### Requirement 5: 入力検証とドメイン前提条件を満たす

**Objective:** パイプラインエンジニアとして、不正な MusicXML / MIDI を静かに受け入れず、品質計算前に落としたい。

#### Acceptance Criteria

1. If MusicXML 入力が存在しない、またはパースできないとき, the Quality Service shall `QualityValidationError` を送出する。
2. If MIDI 入力が存在しない、または読み込めないとき, the Quality Service shall `QualityValidationError` を送出する。
3. The Quality Service shall MusicXML から期待パート一覧を推定できない場合でも処理を継続し、`part_detection_rate` を 0.0 〜 1.0 の範囲で返す。
4. The Quality Service shall ドラムパートを `pitch_range_validity` の音域検査対象から除外する。