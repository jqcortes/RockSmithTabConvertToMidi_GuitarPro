# FRONTEND.md — CLI / API インターフェース仕様

## 1. CLI インターフェース

### 基本使用法

```bash
# シングルファイル / 複数ページ PDF 変換
python -m pipeline convert --input score.pdf --output score.mid

# カスタム設定 + ドロップ D チューニング
python -m pipeline convert --input score.pdf --output score.mid --config config/pipeline.yaml --tuning drop_d

# 検証のみ実行（MIDI は書き出さない）
python -m pipeline convert --input score.pdf --output score.mid --dry-run

# 品質スコア確認
python -m pipeline quality --musicxml score_transformed.xml --midi score.mid
```

### オプション一覧

```
convert コマンド:
  --input PATH          入力ファイル (PDF/PNG/TIFF)
  --output PATH         出力MIDIファイルパス
  --config PATH         設定ファイルパス [default: config/pipeline.yaml]
  --tuning TUNING       ギターチューニング名 [default: standard]
                        config/instrument_map.yaml の tunings を参照
  --quality-threshold F 合格品質スコア閾値 [default: config の quality.pass_threshold]
  --cache-dir PATH      キャッシュディレクトリ [default: .cache/]
  --report PATH         品質レポート出力先 [default: output_dir/quality_report.json]
  --dry-run             実際の変換を行わず検証のみ

quality コマンド:
  --musicxml PATH       入力 MusicXML
  --midi PATH           検証対象 MIDI
  --output-dir PATH     quality_report.json 出力先 [default: MIDI と同じディレクトリ]
```

### 終了コード

| コード | 意味 |
|---|---|
| 0 | 成功 (OQS ≥ threshold) |
| 1 | 警告付き成功 (0.60 ≤ OQS < threshold) |
| 2 | 変換失敗 (OQS < 0.60) |
| 3 | 入力エラー |
| 4 | Audiveris 実行エラー |

---

## 2. 実装状況メモ

- 現在実装されているサブコマンドは `convert` と `quality`
- `convert` は複数ページ PDF をページ単位で処理し、各ページ MIDI を直列結合する
- `--config` で `config/pipeline.yaml` を差し替えられる
- `--tuning` は `config/instrument_map.yaml` の `tunings` を参照する
- `--dry-run` は Transform までを実行し、MIDI と品質レポートは出力しない

---

## 3. 設定ファイル (config/pipeline.yaml)

```yaml
audiveris:
  properties_path: audiveris.properties
  timeout_seconds: 300
  options:
    use_tablature: true
    min_grade: 0.35

preprocessing:
  target_dpi: 300
  min_dpi: 200
  deskew_max_angle: 10.0
  clahe_clip_limit: 2.0

quality:
  pass_threshold: 0.80
  warn_threshold: 0.60
  weights:
    omr_confidence: 0.40
    measure_completeness: 0.30
    pitch_range_validity: 0.15
    part_detection_rate: 0.15

midi:
  default_tempo: 120
  pitch_bend_range: 2  # 半音数
```

現時点で CLI が直接参照するのは次の項目です。

- `audiveris.properties_path`
- `quality.pass_threshold`
- `quality.warn_threshold`

---

*最終更新: 2026-03-13 実装状態同期*
