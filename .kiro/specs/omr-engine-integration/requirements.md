# Requirements Document

## Introduction

前処理済み PNG 画像を入力に Audiveris CLI を実行し、MusicXML を生成する `pipeline/omr/` ドメインの実装。
画像認識 (OMR) の重処理を CLI 経由で呼び出し、キャッシュ・タイムアウト・エラー処理を包括的に管理する。

## Requirements

### Requirement 1: 実行環境の検証

**Objective:** OMR Pipeline として、Java 17+ および Audiveris JAR の存在をパイプライン起動時に確認したい。これにより、実行不可能な状態で長時間処理を開始することを防ぐ。

#### Acceptance Criteria

1. When パイプラインが OMR ステップを開始するとき、the OMR Engine shall Java 実行可能ファイル (`java`) が PATH 上に存在し、バージョンが 17 以上であることを確認する
2. When パイプラインが OMR ステップを開始するとき、the OMR Engine shall 設定ファイル (`config/audiveris.properties` または環境変数 `AUDIVERIS_JAR`) で指定された Audiveris JAR ファイルが存在することを確認する
3. If Java が存在しないか、バージョンが 17 未満の場合, the OMR Engine shall `OmrError` を raise し「Java 17+ が必要です」を含むメッセージを出力する
4. If Audiveris JAR ファイルが存在しない場合, the OMR Engine shall `OmrError` を raise し JAR の期待パスをメッセージに含める
5. The OMR Engine shall 環境検証の結果を `structlog` で構造化ログに記録する

---

### Requirement 2: Audiveris CLI の実行

**Objective:** OMR Pipeline として、前処理済み PNG を入力に `java -jar audiveris.jar -batch -transcribe -export` を実行し MusicXML を生成したい。これにより、楽譜画像を後続ドメインが処理可能なデータ形式に変換できる。

#### Acceptance Criteria

1. When `transcribe(image_path, output_dir)` が呼ばれたとき, the OMR Engine shall `java -jar <audiveris_jar> -batch -transcribe -export -output <output_dir> -- <image_path>` を subprocess で実行する
2. The OMR Engine shall subprocess 実行時に必ず `timeout` パラメータを設定し、デフォルト値は 300 秒とする
3. If subprocess がタイムアウトした場合, the OMR Engine shall プロセスを `kill()` した後 `OmrError` を raise し「Audiveris タイムアウト」をメッセージに含める
4. If Audiveris が 0 以外の終了コードを返した場合, the OMR Engine shall stderr の内容を `OmrError` メッセージに含めて raise する
5. The OMR Engine shall subprocess の stdout/stderr を `structlog` のデバッグログとして記録する
6. The OMR Engine shall CLI 実行の開始・終了時刻を計測し、経過時間を `StepResult.metrics["elapsed_seconds"]` に記録する

---

### Requirement 3: MusicXML 出力の取得と検証

**Objective:** OMR Pipeline として、Audiveris が生成した MusicXML ファイルを確認・取得し、後続ドメインに渡したい。これにより、不完全な出力が次ステップに伝播することを防ぐ。

#### Acceptance Criteria

1. When Audiveris CLI の実行が正常終了したとき, the OMR Engine shall `output_dir` 内の `*.xml` または `*.mxl` ファイルを探索し、出力パスとして取得する
2. If 出力ディレクトリに MusicXML ファイルが存在しない場合, the OMR Engine shall `OmrError` を raise し「MusicXML が生成されませんでした」をメッセージに含める
3. When MusicXML ファイルを取得したとき, the OMR Engine shall `lxml` を使って XML として parse できること (well-formed であること) を確認する
4. If MusicXML が well-formed でない場合, the OMR Engine shall `OmrError` を raise しファイルパスをメッセージに含める
5. The OMR Engine shall 取得した MusicXML ファイルパスを `StepResult.output_path` として返す
6. The OMR Engine shall `StepResult.metrics` に `"musicxml_path"` キーを含める

---

### Requirement 4: ステップキャッシュ

**Objective:** OMR Pipeline として、同一画像に対して Audiveris を再実行しないキャッシュ機能が必要だ。これにより、OMR の長時間処理を繰り返し行わずに済む。

#### Acceptance Criteria

1. When `transcribe(image_path, output_dir)` が呼ばれたとき, the OMR Engine shall `output_dir` に入力画像名に対応する MusicXML が既存の場合、Audiveris CLI を実行せずにキャッシュヒットを返す
2. When キャッシュヒットが発生したとき, the OMR Engine shall `StepResult.metrics["cached"] = True` を含む `StepResult` を返す
3. When キャッシュミスで新規実行した場合, the OMR Engine shall `StepResult.metrics["cached"] = False` を含む `StepResult` を返す
4. The OMR Engine shall キャッシュの有無を `structlog` でログに記録する
5. The OMR Engine shall キャッシュは `output_dir` への書き込みのみで管理し、`pipeline/` 配下に一時ファイルを永続化しない

---

### Requirement 5: エラー階層と伝播

**Objective:** OMR Pipeline として、OMR 固有のエラーを型安全に表現・伝播したい。これにより、呼び出し元が OMR 特有のエラーをピンポイントでキャッチできる。

#### Acceptance Criteria

1. The OMR Engine shall `OmrError` を `PipelineError` のサブクラスとして定義し `pipeline/common.py` の `IngestError` と同じ階層に配置する
2. The OMR Engine shall すべての公開関数・クラスに型ヒントを付け `mypy --strict` が通ることを保証する
3. When 任意のエラーが発生したとき, the OMR Engine shall `OmrError` またはそのサブクラスを raise し、raw な `Exception` や `subprocess.CalledProcessError` をそのまま伝播させない
4. The OMR Engine shall `StepResult(success=False, ...)` ではなく例外による伝播を採用し、部分成功のあいまいな状態を作らない

---

### Requirement 6: 設定と拡張性

**Objective:** OMR Pipeline として、Audiveris のパスやタイムアウトを設定ファイルや環境変数で変更可能にしたい。これにより、異なる環境（CI・ローカル・本番）で設定を切り替えられる。

#### Acceptance Criteria

1. The OMR Engine shall Audiveris JAR パスを `AUDIVERIS_JAR` 環境変数または `config/audiveris.properties` の `audiveris.jar` キーから読み込む（環境変数を優先）
2. The OMR Engine shall Audiveris タイムアウト秒数を `AUDIVERIS_TIMEOUT` 環境変数または `config/audiveris.properties` の `audiveris.timeout` キーから読み込む
3. Where `config/audiveris.properties` が存在する場合, the OMR Engine shall そのファイルから追加 Audiveris CLI オプションを読み込み、CLI 実行時に付加する
4. If 設定ファイルが存在しない場合, the OMR Engine shall デフォルト値（タイムアウト 300 秒）を使用し、警告ログを出力する

