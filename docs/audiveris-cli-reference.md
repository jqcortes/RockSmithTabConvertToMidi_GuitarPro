# audiveris-cli-reference.md — Audiveris CLI LLM向けリファレンス

> このファイルは LLM エージェントが Audiveris CLI を正確に使用するための
> コンパクトなリファレンスです。公式ドキュメント: https://audiveris.github.io/audiveris/

---

## 基本コマンド構文

```bash
audiveris [options] -- <input_file>
```

## 主要オプション

| オプション | 説明 |
|---|---|
| `-batch` | GUI なしでバッチ実行 |
| `-transcribe` | OMR 変換を実行 |
| `-export` | MusicXML にエクスポート |
| `-output <dir>` | 出力ディレクトリ指定 |
| `-option key=value` | Audiveris 内部パラメータ設定 |
| `-input <file>` | 入力ファイル (-- と同等) |

## 重要な内部パラメータ

```bash
# TAB 譜認識有効化
-option org.audiveris.omr.sheet.grid.LineClusterAdapter.useTablature=true

# 信頼度閾値 (低くすると認識増 / 誤認識増)
-option org.audiveris.omr.sig.inter.AbstractInter.minGrade=0.35

# 並列処理数
-option org.audiveris.omr.util.OmrExecutors.corePoolSize=4

# OCR 言語
-option org.audiveris.omr.text.tesseract.TesseractOCR.language=eng
```

## 出力ファイル

| ファイル | 内容 |
|---|---|
| `{bookname}.mxl` | MusicXML (圧縮) |
| `{bookname}.xml` | MusicXML (非圧縮) |
| `{bookname}.omr` | Audiveris ブックファイル (キャッシュ) |

## ローカル実行前提 (Windows)

fixture PDF を end-to-end 変換するには、Python パッケージだけでなく次の外部ツールが必要。

| 前提 | 用途 | 確認コマンド |
|---|---|---|
| Java 17+ | Audiveris 実行 | `java -version` |
| Poppler (`pdfinfo`, `pdftoppm`) | PDF → PNG 変換 (`pdf2image`) | `pdfinfo -v`, `pdftoppm -v` |
| Audiveris JAR | OMR 本体 | `Test-Path <jar-path>` |

Audiveris JAR は次の優先順位で解決される。

1. `AUDIVERIS_JAR` 環境変数
2. `config/audiveris.properties` の `audiveris.jar`

Windows では、まず次の事前確認スクリプトを実行する。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_local_runtime.ps1
```

このスクリプトは Java、Poppler、Audiveris JAR、fixture PDF の有無を確認し、足りない前提があればその場で表示する。

## fixture PDF の変換手順

前提確認がすべて `OK` になったら、次のコマンドで fixture PDF を変換できる。

```powershell
.\.venv\Scripts\python.exe -m pipeline convert \
  --input tests/fixtures/sample_score.pdf \
  --output .cache/manual-check/sample_score.mid
```

期待される成果物:

| パス | 内容 |
|---|---|
| `.cache/manual-check/sample_score.mid` | 生成された MIDI |
| `.cache/manual-check/quality_report.json` | 品質レポート |
| `.cache/ingest/` | PDF から展開された PNG キャッシュ |

## 典型的な失敗原因

| エラー | 原因 | 対処 |
|---|---|---|
| `PDFInfoNotInstalledError` | Poppler が PATH にない | `pdfinfo` / `pdftoppm` を PATH に追加 |
| `java` not found | Java が PATH にない | Java 17+ をインストールして PATH に追加 |
| `Audiveris JAR パスが未設定` | JAR パス未設定 | `AUDIVERIS_JAR` または `config/audiveris.properties` を更新 |
| `MusicXML が生成されませんでした` | Audiveris 実行失敗または認識失敗 | Audiveris ログと input PNG を確認 |

## 典型的な実行例

```bash
# バンドスコア PDF → MusicXML
audiveris -batch -transcribe -export \
  -option org.audiveris.omr.sheet.grid.LineClusterAdapter.useTablature=true \
  -output ./output/ \
  -- band_score.pdf

# 既存 .omr からエクスポートのみ
audiveris -batch -export -output ./output/ -- score.omr
```

## 終了コード

- `0`: 成功
- `非0`: エラー (標準エラー出力を確認)

---

*最終更新: 初版生成 / Audiveris 5.3 準拠*
