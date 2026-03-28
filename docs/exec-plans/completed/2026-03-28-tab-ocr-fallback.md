# 2026-03-28 TAB OCR fallback 実装ログ

## 概要

- 目的: Audiveris が TAB ノートの `string` / `fret` を落としたケースでも、
  前処理済み画像からフレット番号を補完して Transform を継続可能にする
- 対象: Transform ドメイン (`musicxml-transform`)
- コミット: `77cd759` (`Add TAB OCR fallback for transform`)

---

## 実施内容

- `pipeline/transform/tab_ocr.py` を追加
  - 6 本線 TAB スタッフの検出
  - Tesseract TSV 出力の解析
  - OCR トークンの `staff_group / string / fret` へのマッピング
- `pipeline/transform/_transform.py` を更新
  - `preprocessed_image_path` を受け取る
  - 品質ゲート不合格時だけ OCR fallback を実行する
  - `tab_ocr_tokens` / `tab_ocr_applied` / `tab_ocr_skipped` を metrics に追加
- `pipeline/transform/guitar_fixer.py` を更新
  - OCR トークン入力を受け取る
  - TAB ノートの `string` / `fret` 欠損時だけ OCR 結果で補完する
  - 補完結果を既存の pitch 修正ロジックへ渡す
- `pipeline/transform/errors.py` を更新
  - `TransformTabOcrError` を追加
- `pipeline/__main__.py` を更新
  - Transform に前処理済み PNG のパスを渡す

---

## テスト

- `.\.venv\Scripts\python.exe -m pytest tests/unit -v`
  - 結果: `347 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/integration -v`
  - 結果: `3 passed`

---

## 補足

- MVP として、OCR トークン数と TAB ノート数が一致したときだけ補完を適用する
- `tesseract` 未導入環境では warning を残して安全にスキップする
- 次段階では、実ページでの対応付け精度を見ながら
  パート別 / システム別のマッピング強化を検討する
