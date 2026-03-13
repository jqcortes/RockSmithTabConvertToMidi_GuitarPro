# Requirements Document

## Introduction

`midi-render` は、Transform ドメインが出力した補正済み MusicXML を受け取り、
DAW へそのまま取り込める MIDI Type 1 を生成する Render ドメインである。

主な責務は次の 5 点:
1. MusicXML 入力の妥当性確認と MIDI ファイル生成
2. パートロールに基づくチャンネル / プログラム割り当て
3. テンポ・拍子・調号のメタトラック生成
4. ギター奏法の MIDI イベント変換
5. `StepResult` 返却・キャッシュ・エラー階層の提供

---

## Requirements

### Requirement 1: MusicXML から MIDI Type 1 を生成する

**Objective:** DTM 制作者として、Transform 済み MusicXML から複数トラックを持つ標準的な MIDI Type 1 を得たい。

#### Acceptance Criteria

1. When Render ドメインが MusicXML ファイルパスを受け取ったとき, the Render Service shall MusicXML を読み込み、MIDI Type 1 ファイルを `output_dir` に書き出す。
2. When MusicXML に複数の `<part>` が存在するとき, the Render Service shall パートごとに個別の MIDI トラックを生成する。
3. The Render Service shall 出力ファイルパスを `StepResult.output_path` に設定して返す。
4. If 入力 MusicXML が存在しない、または読み込めないとき, the Render Service shall `RenderValidationError` を送出する。

---

### Requirement 2: パートロールに基づいて MIDI チャンネルとプログラムを割り当てる

**Objective:** DTM 制作者として、ギター・ベース・ドラムが適切なチャンネルと GM 楽器で鳴ってほしい。

#### Acceptance Criteria

1. When パートロールが `guitar` のとき, the Render Service shall MIDI Channel 1 / Program 29 を割り当てる。
2. When パートロールが `bass` のとき, the Render Service shall MIDI Channel 2 / Program 33 を割り当てる。
3. When パートロールが `drums` のとき, the Render Service shall MIDI Channel 10 を割り当て、Program Change を送らない。
4. When パートロールが `other` のとき, the Render Service shall 空きチャンネルを順に割り当て、Channel 10 は予約済みとしてスキップする。
5. The Render Service shall 割り当て結果を `StepResult.metrics["channel_map"]` に辞書形式で記録する。

---

### Requirement 3: メタトラックとテンポ情報を生成する

**Objective:** DAW 利用者として、テンポ・拍子・調号が失われずに MIDI に含まれていてほしい。

#### Acceptance Criteria

1. The Render Service shall Track 0 をメタトラックとして生成し、テンポ・拍子記号・調号を格納する。
2. When MusicXML に `<metronome>` または `<sound tempo="...">` が存在するとき, the Render Service shall tempo change イベントを MIDI に反映する。
3. If テンポ情報が見つからないとき, the Render Service shall 120 BPM を使用し、`StepResult.warnings` に既定テンポ適用を記録する。
4. The Render Service shall 生成したテンポイベント数を `StepResult.metrics["tempo_events"]` に記録する。

---

### Requirement 4: ギター奏法を MIDI イベントへ変換する

**Objective:** ギタリストとして、MusicXML に保持された奏法が MIDI 再生でもある程度再現されてほしい。

#### Acceptance Criteria

1. When `<bend>` 要素がノートに存在するとき, the Render Service shall Pitch Bend イベント列へ変換する。
2. When `<slide>` 要素が存在するとき, the Render Service shall Pitch Bend を使って開始音から目標音への移動を表現する。
3. When `<palm-mute>` 要素が存在するとき, the Render Service shall Expression CC#11 の低減と音価短縮を適用する。
4. When `<hammer-on>` または `<pull-off>` が存在するとき, the Render Service shall ベロシティを減衰させたレガート表現を適用する。
5. The Render Service shall 奏法変換件数を `StepResult.metrics["techniques_rendered"]` に記録する。

---

### Requirement 5: キャッシュ・エラー処理・公開 API を提供する

**Objective:** パイプラインエンジニアとして、Render ステップを再実行しやすくし、失敗種別も上位レイヤから識別したい。

#### Acceptance Criteria

1. The Render Service shall `PipelineError` を継承した `RenderError` 基底クラスを持ち、少なくとも `RenderValidationError` と `RenderExecutionError` を提供する。
2. When `output_dir/{stem}.mid` が既に存在するとき, the Render Service shall キャッシュヒットとして再生成をスキップし、`StepResult.metrics["cached"] = True` を返す。
3. The Render Service shall 公開エントリポイント関数 `render(musicxml_path: Path, output_dir: Path) -> StepResult` を `pipeline/render/__init__.py` から re-export する。
4. The Render Service shall すべての公開関数・クラスに型ヒントを付与し、`mypy --strict` 相当で通る実装とする。
5. The Render Service shall `print()` を使用せず、診断ログを `structlog` で出力する。