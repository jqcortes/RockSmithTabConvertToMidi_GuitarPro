# Implementation Plan — musicxml-transform

## Task Overview

| # | タスク | 並列 | 要件カバレッジ |
|---|--------|------|--------------|
| 1 | 例外階層を実装する | — | 5.1, 5.2 |
| 2 | MusicXML バリデーション機能を実装する | — | 1.1〜1.5 |
| 3 | ギター TAB 補正機能を実装する | — | 2.1〜2.6 |
| 4 | パート識別機能を実装する | P | 3.1〜3.5 |
| 5 | 信頼度フィルタ機能を実装する | P | 4.1〜4.4 |
| 6 | エントリポイントとキャッシュ制御を実装する | — | 5.3, 5.4, 6.1〜6.5 |
| 7 | テストフィクスチャとユニットテスト整備 | — | 全要件 |

---

## Tasks

- [x] 1. Transform ドメインの例外階層を実装する
- [x] 1.1 `TransformError` を基底クラスとして定義し、3 つのサブクラスを用意する
  - `PipelineError` を継承した `TransformError` 基底クラスを作成する
  - `TransformValidationError`（MusicXML 入力不正）、`TransformGuitarFixerError`（TAB 解析失敗）、`TransformPartError`（パート識別失敗）の 3 サブクラスを定義する
  - `pipeline/omr/errors.py` と同じシンプルな継承のみ（状態なし）のパターンを使う
  - `mypy --strict` 相当の型チェックが通ることを確認する
  - _Requirements: 5.1, 5.2_
- [x] 1.2 例外クラスのユニットテストを作成する
  - 各クラスが正しい親クラスを継承していることを確認するテストを書く
  - `PipelineError` として一括 catch できることを確認するテストを書く
  - エラーメッセージが保持されることを確認するテストを書く
  - _Requirements: 5.1, 5.2_

- [x] 2. MusicXML 入力バリデーション機能を実装する
- [x] 2.1 `.xml` 平文フォーマットの読み込みとバリデーションを実装する
  - `lxml.etree.parse()` で XML を読み込み、パース失敗時は `TransformValidationError` を送出する
  - ルート要素が `score-partwise` または `score-timewise` であることを確認し、違反時は `TransformValidationError` を送出する
  - ファイル不在時（`FileNotFoundError`）は `TransformValidationError` に変換して送出する
  - パート数・小節数・スタッフ数を XPath で集計して `ValidationResult` に格納する
  - _Requirements: 1.1, 1.2, 1.4, 1.5_
- [x] 2.2 `.mxl`（ZIP 形式）フォーマットの展開とバリデーションを追加する
  - `zipfile.ZipFile` で `.mxl` を展開し、内包する XML ファイルを特定する
  - 展開した XML データに対して 2.1 と同じ検証ロジックを適用する
  - ZIP 展開失敗時も `TransformValidationError` を送出する
  - `pipeline/omr/finder.py` の `_validate_mxl` パターンを参考にする
  - _Requirements: 1.3_
- [x] 2.3 バリデーションのユニットテストを作成する
  - 正常な `.xml` ファイルを渡して `ValidationResult` が返ることを確認する
  - 正常な `.mxl` ファイルを渡して同様の結果が返ることを確認する
  - 不正 XML を渡したときに `TransformValidationError` が発生することを確認する
  - 存在しないファイルパスで `TransformValidationError` が発生することを確認する
  - ルート要素が不正（例: `<foo>`）のときに `TransformValidationError` が発生することを確認する
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 3. ギター TAB 補正機能を実装する
- [x] 3.1 TAB スタッフの識別ロジックを実装する
  - `<clef sign="TAB">` または `<staff-lines>6</staff-lines>` の存在を XPath で確認して TAB スタッフを識別する
  - TAB スタッフが存在しない場合は pitch 上書きをスキップし、入力ツリーをそのまま返す
  - 識別結果をログ（structlog）に記録する
  - _Requirements: 2.1, 2.6_
- [x] 3.2 フレット番号からMIDIピッチへの変換ロジックを実装する
  - `fret_to_pitch(string, fret, tuning)` を実装する（`pitch = tuning[6 - string] + fret`）
  - `STANDARD_TUNING = [40, 45, 50, 55, 59, 64]`（E2 A2 D3 G3 B3 E4）をデフォルトとして定義する
  - 計算した MIDI ピッチ番号を MusicXML の `<step>`, `<octave>`, `<alter>` 要素に正確に変換して上書きする
  - フレット番号や弦番号が欠損・非数値の場合は `fixer_skipped` カウンタを増やしてそのノートをスキップする
  - _Requirements: 2.1, 2.2, 2.5_
- [x] 3.3 `config/instrument_map.yaml` からのチューニング読み込みを実装する
  - `config/instrument_map.yaml` の `tunings:` セクションを読み込む `load_tuning(name)` を実装する
  - ファイルが存在しない場合・指定名が未定義の場合は `STANDARD_TUNING` をデフォルトとして使用する
  - `config/instrument_map.yaml` を `standard`・`drop_d`・`half_step_down` 等のチューニング定義付きで新規作成する
  - _Requirements: 2.3_
- [x] 3.4 `<bend>` 要素の保持と `apply()` の最終組み上げを行う
  - pitch 書き換えを行う際に `<technical><bend>` 要素には一切触れないことを確認する
  - TAB スタッフのノートと五線譜スタッフのノートを拍位置（`measure number` + `beat`）でマッチングして上書きする
  - 成功件数 `fixer_applied`、スキップ件数 `fixer_skipped` を `FixerResult` に記録する
  - structlog で変換結果を記録する
  - _Requirements: 2.1, 2.4, 2.5_
- [x] 3.5 ギター補正機能のユニットテストを作成する
  - TAB スタッフありの MusicXML で pitch が正しく上書きされることを確認する
  - TAB スタッフなしの MusicXML でスキップされることを確認する
  - 各チューニング（standard / drop_d / half_step_down）でピッチ計算が正確なことを確認する
  - `<bend>` 要素が補正後も保持されていることを確認する
  - fret/string 欠損時に `fixer_skipped` が増加することを確認する
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 4. (P) パート情報の正規化機能を実装する
  - タスク 3 の `GuitarFixer` とは独立したコンポーネントのため並列実装可能
- [x] 4.1 (P) Audiveris 出力を前提にしたパートロール正規化ロジックを実装する
  - `<score-instrument><instrument-name>` のテキストと clef 種別を補助情報として `guitar / bass / drums / other` を正規化する（大文字小文字を区別しない）
  - TAB clef の存在（2スタッフ構成）は Audiveris が出力した既存パート境界を補強する証拠としてのみ使用する
  - ギターの五線譜+TABの2スタッフ構成は `PartInfo.tab_staff_id` に TAB スタッフ ID を記録するが、既存の `part` 構造を再分割・再構成しない
  - 判定できないパートのロールは `"other"` とし、パート名を `warnings` リストに追加する
  - パート名・ロールを辞書形式で `PartIdentifierResult.parts_map` に格納する
  - _Requirements: 3.1, 3.2, 3.4, 3.5_
- [x] 4.2 (P) 正規化済みロールを XML に補助属性として付加する機能を実装する
  - `<part>` 要素に `transform:role` カスタム属性を付加する `annotate()` を実装する
  - 下流の Render ドメインが参照できる形式で XML に記録する
  - 既存の `part-list` / `score-part` / `part` 構造は変更しない
  - `etree.tostring()` での serialization 後も属性が保持されることを確認する
  - _Requirements: 3.3_
- [x] 4.3 パート識別機能のユニットテストを作成する
  - ギター（TAB あり）・ベース・ドラムを含む multipart MusicXML で各ロールが正しく判定されることを確認する
  - 2スタッフ構成（五線譜+TAB）が1論理パートに統合されることを確認する
  - 判定不能なパートが `"other"` になり warnings に記録されることを確認する
  - `annotate()` 後の XML に `transform:role` 属性が含まれることを確認する
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 5. (P) 信頼度フィルタの拡張ポイントを実装する
  - タスク 3・4 とは独立したコンポーネントのため並列実装可能
- [x] 5.1 (P) 明示的な信頼度属性が存在する場合だけノード除外ロジックを実装する
  - `<note confidence="...">` カスタム属性が存在するノードのみフィルタ対象とする
  - `confidence < 0.5`（`THRESHOLD`）の場合、そのノードを XML ツリーから削除する
  - `confidence` 属性が存在しないノートは信頼度 1.0 とみなしてスキップ（除外しない）する
  - Audiveris 標準出力のみを根拠に Transform 側で独自の confidence を推定しない
  - 除外したノートの小節番号・パート名・ピッチを `removed` リストに記録する
  - `total` カウント（全ノート数）と `filter_rate = len(removed) / total` を計算する
  - _Requirements: 4.1, 4.2, 4.3, 4.4_
- [x] 5.2 信頼度フィルタのユニットテストを作成する
  - `confidence` 属性付きノードを持つ MusicXML で閾値未満のノートが除外されることを確認する
  - `confidence` 属性のないノートが除外されないことを確認する
  - `filter_rate` の計算が正しいことを確認する
  - `removed` リストに除外ノートの情報が記録されることを確認する
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 6. エントリポイントとキャッシュ制御を組み上げる
- [x] 6.1 `transform()` エントリポイント関数を実装する
  - `MusicXmlValidator` 実行後に Audiveris 出力の品質ゲートを判定し、必要時のみ `GuitarFixer → PartIdentifier → ConfidenceFilter` を走らせる変換パイプラインを実装する
  - 品質ゲートを満たした場合は Audiveris 出力をほぼそのまま通し、必要最小限のメタデータ整形だけを行う
  - 各変換器から得たメトリクス（`fallback_required`, `fallback_reasons`, `fixer_applied`, `fixer_skipped`, `filtered_notes`, `filter_rate`, `part_count` 等）を集約して `StepResult.metrics` に格納する
  - 変換完了後の XML を `etree.tostring(encoding="unicode")` で `output_dir/{stem}_transformed.xml` に書き出す
  - `structlog` で処理開始・完了・エラーを構造化ログとして記録し、`print()` は一切使用しない
  - _Requirements: 5.3, 5.4, 6.1, 6.4, 6.6, 6.7_
- [x] 6.2 キャッシュファースト制御を実装する
  - `output_dir/{stem}_transformed.xml` が存在する場合は変換処理をスキップして `cached=True` の `StepResult` を返す
  - キャッシュヒット時も `structlog` でログを出力する
  - これは `pipeline/omr/_transcribe.py` と同じキャッシュファーストパターンに従う
  - _Requirements: 6.2_
- [x] 6.3 `pipeline/transform/__init__.py` から `transform()` を re-export する
  - `__init__.py` で `transform()` を唯一の公開 API として re-export する
  - `pipeline/transform` を `import` するだけで `transform()` が使えることを確認する
  - _Requirements: 6.3_
- [x] 6.4 予期しない例外のラッピングと失敗時 StepResult を実装する
  - 変換パイプライン内で `TransformError` 以外の例外が発生した場合、`TransformError` でラップして `structlog` にスタックトレースと共に記録して再送出する
  - 必要に応じて例外を握りつぶす場合は `StepResult(success=False, ...)` を返す（設計書の判断基準に従う）
  - _Requirements: 5.3, 6.5_
- [x] 6.5 `transform()` のユニットテストを作成する
  - キャッシュヒット時（既存ファイルあり）に変換がスキップされ `cached=True` で返ることを確認する
  - キャッシュミス時（ファイルなし）に品質ゲート判定が呼ばれ、fallback 必要時だけ救済変換器が呼ばれて `output_dir` にファイルが書き出されることを確認する
  - 品質ゲート通過時は不要な救済処理が走らないことを確認する
  - 変換失敗時（`TransformValidationError` 等）に適切な例外が伝播することを確認する
  - `StepResult.metrics` に期待するキー（`cached`, `fallback_required`, `fixer_applied` 等）が含まれることを確認する
  - `print()` が呼ばれないことを確認する（structlog モック）
  - _Requirements: 5.3, 5.4, 6.1, 6.2, 6.4, 6.5, 6.6, 6.7_

- [x] 7. テストフィクスチャとテストスイート全体の整備
- [x] 7.1 テスト用 MusicXML フィクスチャを作成する
  - `tests/fixtures/musicxml/simple_guitar_tab.xml` — 五線譜 + TAB の 2 スタッフ構成サンプルを作成する
  - `tests/fixtures/musicxml/no_tab.xml` — TAB スタッフなし（pitch 保持テスト用）を作成する
  - `tests/fixtures/musicxml/invalid.xml` — 不正 XML（バリデーションエラーテスト用）を作成する
  - `tests/fixtures/musicxml/multipart.xml` — ギター・ベース・ドラムの 3 パート構成を作成する
  - `tests/fixtures/musicxml/with_confidence.xml` — `confidence` 属性付きノードを含むサンプルを作成する
  - _Requirements: 1.1, 1.3, 2.1, 3.1, 4.1_
- [x] 7.2 テストスイート全体の統合確認と mypy 検証を行う
  - `tests/unit/test_transform/` ディレクトリに `__init__.py` を配置してサブパッケージ化する
  - `python -m pytest tests/unit/test_transform/ --cov=pipeline/transform --cov-report=term-missing` でカバレッジ 95%+ を達成する
  - `python -m mypy pipeline/transform/ --strict` でエラーゼロを確認する
  - 全テストが `159 + 新規` passed で完了することを確認する
  - _Requirements: 6.4_
