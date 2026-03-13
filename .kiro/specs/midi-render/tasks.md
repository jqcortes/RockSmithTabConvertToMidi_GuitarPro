# Implementation Plan — midi-render

## Task Overview

| # | タスク | 並列 | 要件カバレッジ |
|---|---|---|---|
| 1 | Render 例外階層を実装する | — | 5.1 |
| 2 | チャンネル割り当て機能を実装する | P | 2.1-2.5 |
| 3 | テンポ / メタトラック解決を実装する | P | 3.1-3.4 |
| 4 | MIDI レンダラ本体を実装する | — | 1.1-1.4 |
| 5 | ギター奏法レンダリングを実装する | P | 4.1-4.5 |
| 6 | エントリポイントとキャッシュを実装する | — | 5.2-5.5 |
| 7 | フィクスチャとユニットテストを整備する | — | 全要件 |

---

## Tasks

- [x] 1. Render ドメインの例外階層を実装する
- [x] 1.1 `RenderError`、`RenderValidationError`、`RenderExecutionError` を定義する
  - `PipelineError` を継承した基底 / サブクラスを実装する
  - 対応ユニットテストを書く
  - _Requirements: 5.1_

- [x] 2. (P) パートロールに基づくチャンネル割り当てを実装する
- [x] 2.1 `ChannelMapper` を実装する
  - `guitar` → Ch.1 / Program 29
  - `bass` → Ch.2 / Program 33
  - `drums` → Ch.10 / Program なし
  - `other` → 空きチャンネルを順に割り当てる
  - 割り当て結果をメトリクス化できる構造で返す
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. (P) テンポとメタトラック構築を実装する
- [x] 3.1 `TempoResolver` を実装する
  - テンポ・拍子・調号を Track 0 用イベントへ変換する
  - テンポ未指定時は 120 BPM と warning を返す
  - tempo change 数をメトリクス化する
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. MIDI レンダラ本体を実装する
- [x] 4.1 `MidiRenderer` で MusicXML から MIDI Type 1 を生成する
  - パートごとに個別トラックを生成する
  - channel / program 割り当てを適用する
  - 出力 `.mid` を書き出す
  - _Requirements: 1.1, 1.2, 1.3_
- [x] 4.2 入力検証と読み込み失敗を `RenderValidationError` に変換する
  - _Requirements: 1.4_

- [x] 5. (P) ギター奏法レンダリングを実装する
- [x] 5.1 `TechniqueRenderer` を実装する
  - bend を Pitch Bend へ変換する
  - slide を Pitch Bend グライドへ変換する
  - palm-mute を CC#11 と音価短縮へ変換する
  - hammer-on / pull-off をベロシティ減衰付きレガートへ変換する
  - `techniques_rendered` を集計する
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6. エントリポイントとキャッシュを実装する
- [x] 6.1 `render(musicxml_path, output_dir) -> StepResult` を実装する
  - `output_dir/{stem}.mid` のキャッシュヒットを先に確認する
  - `StepResult.metrics` に `cached`、`channel_map`、`tempo_events`、`techniques_rendered` を含める
  - `pipeline/render/__init__.py` から re-export する
  - `print()` を使わず `structlog` を用いる
  - _Requirements: 5.2, 5.3, 5.4, 5.5_

- [x] 7. フィクスチャとユニットテストを整備する
- [x] 7.1 Render 用 MusicXML fixture を追加する
  - guitar / bass / drums を含む multipart fixture を追加する
  - bend / slide / palm-mute 付き fixture を追加する
  - _Requirements: 1.1, 2.1, 4.1_
- [x] 7.2 ユニットテストと検証を追加する
  - `tests/unit/test_render/` を作成する
  - `pytest --cov=pipeline/render --cov-report=term-missing` でカバレッジ 95%+ を確認する
  - `python -m mypy pipeline/render --strict` を通す
  - _Requirements: 全要件_