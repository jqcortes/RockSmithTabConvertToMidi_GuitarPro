# Requirements Document

## Introduction

`musicxml-transform` は、Audiveris OMR が出力した MusicXML を受け取り、ギタリスト・DTM 制作者が即座に MIDIレンダリングへ渡せる「補正済み MusicXML」に変換するパイプライン Transform ドメインである。

主な責務は次の 5 点:
1. MusicXML の well-formed / schema 検証
2. タブ譜優先補正 — Audiveris 出力が不十分な場合に限り、TAB スタッフのフレット情報を五線譜 pitch の正解として採用
3. パート情報の正規化 — Audiveris が出力したパート構造を後続が参照しやすい形に整える
4. 信頼度フィルタリング — 明示的な信頼度属性がある場合のみ `quality_score < 0.5` のノートを除外し警告記録
5. `StepResult` 返却・キャッシュ — 後続 Render ドメインへファイルパスで渡す

---

## Requirements

### Requirement 1: MusicXML 入力バリデーション

**Objective:** パイプラインエンジニアとして、Transform ドメインへ渡された MusicXML が構文・構造ともに正しいことを確認したい。不正な入力は後続処理を汚染する前に早期検出する。

#### Acceptance Criteria

1. When Transform ドメインがファイルパスを受け取ったとき, the Transform Service shall lxml で XML の well-formed 性を検証し、パース失敗時は `TransformValidationError` を送出する。
2. When MusicXML ファイルが well-formed と確認されたとき, the Transform Service shall `<score-partwise>` または `<score-timewise>` がルート要素として存在することを確認する。存在しない場合は `TransformValidationError` を送出する。
3. When MusicXML ファイルが `.mxl` 拡張子であるとき, the Transform Service shall `zipfile` でアーカイブを展開し、内包する XML を取得してから検証を行う。
4. If 入力ファイルが存在しないとき, the Transform Service shall `TransformValidationError` を送出し、処理を中断する。
5. The Transform Service shall バリデーション結果（パート数・小節数・スタッフ数）を `StepResult.metrics` に含める。

---

### Requirement 2: タブ譜優先ギター補正

**Objective:** ギタリストとして、五線譜の音域解釈ミスでなく TAB 譜のフレット情報を正しい pitch として MIDI に反映させたい。

#### Acceptance Criteria

1. When MusicXML に TAB スタッフ（6 線 / clef type `TAB`）と五線譜スタッフが同一論理パートに共存し、かつ Audiveris 出力が定義済み品質ゲートを下回るとき, the Guitar Fixer shall TAB スタッフの `<technical><fret>` および `<technical><string>` 要素を読み取り、五線譜ノートの `<pitch>` を上書きする。
2. When フレット番号と弦番号が確定されたとき, the Guitar Fixer shall `STANDARD_TUNING = [E2, A2, D3, G3, B3, E4]`（MIDI 40, 45, 50, 55, 59, 64）を基準にピッチ計算を行う（`pitch = open_pitch + fret`）。
3. Where `config/instrument_map.yaml` にチューニング設定が存在するとき, the Guitar Fixer shall 配置されたチューニング（`drop_d`, `half_step_down` 等）でピッチ計算を行い、デフォルトは `standard` を使用する。
4. When `<bend>` 要素が TAB スタッフにあるとき, the Guitar Fixer shall `<bend-alter>` の半音数を MusicXML の `<technical>` 要素として保持し、下流 Render ドメインが Pitch Bend イベントに変換できる形式をそのまま残す。
5. The Guitar Fixer shall 補正したノート数・補正失敗（フレット/弦情報欠損）の件数を `StepResult.metrics["fixer_applied"]` および `metrics["fixer_skipped"]` に記録する。
6. If TAB スタッフが存在しないとき、または Audiveris 出力が品質ゲートを満たしていて補正不要と判定されたとき, the Guitar Fixer shall pitch 上書きをスキップし、元の MusicXML の pitch をそのまま保持する。

---

### Requirement 3: パート情報の正規化

**Objective:** DTM 制作者として、Audiveris が出力した既存の `part-list` / スタッフ構造を尊重しつつ、後続の MIDI チャンネル割り当てに必要なパート情報だけを安定して参照したい。

#### Acceptance Criteria

1. When MusicXML の `<part-list>` が解析されたとき, the Part Identifier shall Audiveris が既に出力した `<score-part>` / `<score-instrument>` / スタッフ構造を正として読み取り、後続が参照しやすいメタデータへ正規化する。
2. When ギターパートに「五線譜スタッフ + TAB スタッフ」の 2 スタッフ構成が検出されたとき, the Part Identifier shall Audiveris の既存パート境界を崩さずに、この構成を 1 論理ギターパートとして注記する。
3. The Part Identifier shall 各論理パートのロール情報を `<part>` 要素のカスタム属性またはメタ辞書として補正済み MusicXML に付加してよいが、既存の `part` / `score-part` 構造を再分割してはならない。
4. If パートロールが Audiveris 出力から自動判定できないとき, the Part Identifier shall ロールを `"other"` とし、`StepResult.warnings` に未判定パート名を追記する。
5. The Part Identifier shall パート数・各ロールのパート名を `StepResult.metrics["parts"]` に辞書形式で記録する。

---

### Requirement 4: 信頼度フィルタリング

**Objective:** パイプラインエンジニアとして、将来的に上流または Quality ドメインが付与した信頼度属性を利用して低品質ノートを除外できるようにしたい。ただし Audiveris 標準 MusicXML に存在しない情報を Transform で捏造したくない。

#### Acceptance Criteria

1. The Transform Service shall MusicXML の各ノートに明示的な信頼度属性（`<notations>` 内カスタム要素または属性 `confidence`）が存在する場合のみ、それを解釈して `quality_score < 0.5` のノートを補正済み MusicXML から除外する。
2. When ノートが除外されたとき, the Transform Service shall そのノートの小節番号・パート名・ピッチを `StepResult.warnings` に記録し、`StepResult.metrics["filtered_notes"]` カウンタを増分する。
3. If ノートに信頼度属性が存在しないとき, the Transform Service shall そのノートを信頼度 1.0 とみなして除外せず処理を続行する。
4. The Transform Service shall 除外率（`filtered_notes / total_notes`）を `StepResult.metrics["filter_rate"]` として記録する。
5. The Transform Service shall Audiveris 標準出力だけを根拠に独自のノート信頼度を推定・付与してはならない。

---

### Requirement 5: エラー処理階層

**Objective:** パイプラインエンジニアとして、Transform ドメインで発生した障害を種別ごとに識別し、上位レイヤが適切にハンドリングできる例外階層を持ちたい。

#### Acceptance Criteria

1. The Transform Service shall `PipelineError` を継承した `TransformError` 基底クラスを持ち、すべての Transform 固有例外はこれを継承する。
2. The Transform Service shall 次のサブクラスを提供する: `TransformValidationError`（入力 MusicXML が不正）、`TransformGuitarFixerError`（TAB 解析失敗）、`TransformPartError`（パート識別失敗）。
3. If Transform ドメイン内で予期しない例外が発生したとき, the Transform Service shall それを `TransformError` でラップして再送出し、スタックトレースを `structlog` で記録する。
4. The Transform Service shall `print()` を一切使用せず、すべての診断ログを `structlog` で構造化 JSON として出力する。

---

### Requirement 6: StepResult 返却・キャッシュ

**Objective:** パイプラインエンジニアとして、Transform ステップ結果をディスクにキャッシュし、同一入力に対するスキップ再実行を実現したい。

#### Acceptance Criteria

1. When Transform が正常完了したとき, the Transform Service shall 補正済み MusicXML を指定 `output_dir` に書き出し、そのパスを `StepResult.output_path` に設定して返す。
2. When Transform ドメインが呼ばれたとき, the Transform Service shall `output_dir` に既存の補正済みファイルが存在する場合はキャッシュヒットとみなし、CLI 処理をスキップして `StepResult.metrics["cached"] = True` で返す。
3. The Transform Service shall公開エントリポイント関数 `transform(musicxml_path: Path, output_dir: Path) -> StepResult` を `pipeline/transform/__init__.py` から re-export する。
4. The Transform Service shall 型ヒントを全公開関数・クラスに付与し、`mypy --strict` 相当で静的型検査が通る実装とする。
5. When Transform が失敗したとき, the Transform Service shall `StepResult(success=False, output_path=None, metrics={}, warnings=[...])` を返す（例外を呑む場合のみ。基本は例外送出を優先）。
6. The Transform Service shall Audiveris 出力の品質ゲート（例: TAB スタッフ欠落、part 情報欠落、小節整合性エラー、pitch/TAB 矛盾）を評価し、救済処理が必要な場合のみ Guitar Fixer / Part Identifier / Confidence Filter を実行する。
7. The Transform Service shall 品質ゲートを満たす場合、Audiveris 出力をほぼそのまま通しつつ、必要最小限の検証とメタデータ整形だけを行う。

