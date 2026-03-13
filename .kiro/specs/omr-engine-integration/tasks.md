# Implementation Plan — omr-engine-integration

## Task Format

- `(P)` = 並列実行可能タスク
- `*` = オプション（MVP 後に対応可）

---

## Tasks

- [x] 1. OMR ドメイン固有のエラー階層を定義する
  - `pipeline/omr/` ディレクトリと `__init__.py` を作成する
  - `OmrError` を `PipelineError` のサブクラスとして定義し、`OmrEnvironmentError`・`OmrTimeoutError`・`OmrExecutionError`・`OmrOutputError` の 4 種を派生させる
  - raw な `subprocess` 例外を外部に漏らさないことを型レベルで保証する
  - すべてのクラスに型ヒントを付け `mypy --strict` が通ることを確認する
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 2. (P) Audiveris 実行設定をロードする機能を実装する
  - `AUDIVERIS_JAR` 環境変数 → `config/audiveris.properties` の `audiveris.jar` キー の優先順で JAR パスを解決する
  - `AUDIVERIS_TIMEOUT` 環境変数 → `config/audiveris.properties` の `audiveris.timeout` キー → デフォルト 300 秒の優先順でタイムアウトを解決する
  - `config/audiveris.properties` が存在しない場合は警告ログを出力してデフォルト値で続行する
  - `config/audiveris.properties` が存在する場合はそこに記載された追加 Audiveris オプションも読み込む
  - 解決済み設定を不変オブジェクトとして返す
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 3. Java と Audiveris JAR の実行環境を検証する機能を実装する
  - `java -version` を実行して Java 17 以上であることを確認する
  - 指定された Audiveris JAR ファイルの存在を確認する
  - Java が見つからないか 17 未満の場合は `OmrEnvironmentError` を raise する
  - JAR が存在しない場合は期待パスを含む `OmrEnvironmentError` を raise する
  - 検証結果を `structlog` で構造化ログに記録する
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 4. (P) Audiveris CLI を subprocess で実行する機能を実装する
  - `java -jar <jar> -batch -transcribe -export -output <dir> -- <image>` の形式でコマンドリストを構築する
  - TAB 譜認識オプション等のデフォルト Audiveris オプションをコマンドに付加する
  - `shell=False` のリスト形式引数で subprocess を実行し、コマンドインジェクションを防止する
  - 実行には必ず `timeout` を設定し、タイムアウト時はプロセスを強制終了して `OmrTimeoutError` を raise する
  - Audiveris が 0 以外の終了コードを返した場合は stderr を含む `OmrExecutionError` を raise する
  - stdout/stderr を `structlog` の DEBUG ログに記録し、経過時間をメトリクスとして計測する
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 5. (P) 出力 MusicXML を探索・検証する機能を実装する
  - 出力ディレクトリ内の `.mxl` ファイルを優先して探索し、見つからなければ `.xml` を探す
  - `.mxl` は ZIP として展開したうえで `lxml` で well-formed 確認を行う
  - `.xml` は直接 `lxml` で well-formed 確認を行う
  - MusicXML ファイルが見つからない場合は `OmrOutputError` を raise する
  - well-formed でない場合はファイルパスを含む `OmrOutputError` を raise する
  - 検証済み MusicXML のファイルパスを返す
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 6. 公開エントリーポイント `transcribe()` をキャッシュ機能とともに実装する
  - `transcribe(image_path, output_dir)` を唯一の公開 API として `pipeline/omr/__init__.py` から re-export する
  - 呼び出し時に `.kiro/specs` の設定ロード → 環境検証 → キャッシュ確認 → CLI 実行 → MusicXML 探索の順で処理する
  - 出力ディレクトリに同名 MusicXML が既存の場合は Audiveris を再実行せずキャッシュ済みとして `StepResult` を返す
  - キャッシュヒット時は `StepResult.metrics["cached"] = True`、ミス時は `False` を設定する
  - `StepResult.metrics` に `musicxml_path`・`elapsed_seconds`・`cached` を含める
  - キャッシュの有無を `structlog` で記録する
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 7. OMR ドメインのユニットテストを整備する
- [x] 7.1 (P) エラー階層のテストを書く
  - `OmrError` が `PipelineError` のサブクラスであることをテストする
  - 4 種のサブクラスが `OmrError` を継承していることをテストする
  - _Requirements: 5.1, 5.2, 5.3, 5.4_
- [x] 7.2 (P) 設定ロードのテストを書く
  - 環境変数が設定ファイルより優先されることをテストする
  - 設定ファイル不在時にデフォルト値が使われることをテストする
  - タイムアウト・JAR パスの解決ロジックをテストする
  - _Requirements: 6.1, 6.2, 6.3, 6.4_
- [x] 7.3 (P) 環境検証のテストを書く
  - Java 17+ が検出される場合の成功をテストする
  - Java 未インストール・バージョン不足時に `OmrEnvironmentError` が raise されることをテストする
  - JAR ファイル不在時に `OmrEnvironmentError` が raise されることをテストする
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
- [x] 7.4 (P) CLI 実行のテストを書く
  - `subprocess.run` をモック化して正常終了時の動作をテストする
  - タイムアウト時に `OmrTimeoutError` が raise されることをテストする
  - 終了コード非0時に `OmrExecutionError` が raise されることをテストする
  - コマンドが `shell=False` かつリスト形式で構築されることをテストする
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
- [x] 7.5 (P) MusicXML 探索・検証のテストを書く
  - `.mxl` 優先・`.xml` フォールバックの探索順序をテストする
  - MusicXML 不在時に `OmrOutputError` が raise されることをテストする
  - well-formed でない XML に対して `OmrOutputError` が raise されることをテストする
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
- [x] 7.6 `transcribe()` のキャッシュ統合テストを書く
  - キャッシュヒット時に `AudiverisRunner` が呼ばれないことをモックでテストする
  - キャッシュミス時にフル処理が実行されることをテストする
  - `StepResult` に必要なメトリクスキーが含まれることをテストする
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
- [x]* 7.7 カバレッジ計測を行い `pipeline/omr/` が 80% 以上であることを確認する
  - `pytest --cov=pipeline/omr --cov-report=term-missing` でカバレッジを計測する
  - 80% を下回るモジュールを特定し不足テストを追加する
  - _Requirements: 5.1, 5.2, 5.3, 5.4_
