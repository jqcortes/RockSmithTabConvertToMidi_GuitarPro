# musicxml-transform: Transform ドメインの仕様駆動実装

**ステータス**: 実装完了・実地検証継続  
**優先度**: 🔴 高  
**担当**: -  
**起票日**: 2026-03-13  

---

## 概要

`musicxml-transform` spec に基づいて、Transform ドメインの
MusicXML 検証・品質ゲート判定・条件付き TAB 補正・パート正規化・信頼度フィルタ・エントリポイントを
TDD で段階的に実装する。

現状、`.kiro/specs/musicxml-transform/` は requirements / design / tasks まで揃っており、
Transform ドメインの主要実装は完了している。直近では TAB 技術情報が欠落した
Audiveris 出力に対して、前処理済み PNG と外部 Tesseract を使った
TAB OCR fallback を追加した。

---

## 最新進捗 (2026-03-28)

- `pipeline/transform/tab_ocr.py` を追加し、6 本線 TAB スタッフ検出と
  Tesseract TSV 解析によるフレット番号抽出の MVP を実装した
- `transform()` に `preprocessed_image_path` を渡し、
  品質ゲート不合格時のみ OCR fallback を試す経路を追加した
- `GuitarFixer.apply()` に OCR トークン入力を追加し、
  TAB ノートの `string` / `fret` 欠損時だけ補完できるようにした
- `TransformTabOcrError` を追加し、TAB OCR failure を Transform 例外階層へ統合した
- ユニットテストと CLI 配線テストを追加した
- コミット: `77cd759` (`Add TAB OCR fallback for transform`)
- 実行確認:
  - `python -m pytest tests/unit -v` → `347 passed`
  - `python -m pytest tests/integration -v` → `3 passed`

---

## フェーズ分解

| タスク | 状態 | 説明 |
|---|---|---|
| 1. 例外階層 | ✅ 完了 | `TransformTabOcrError` を含む例外階層とテストを実装 |
| 2. MusicXML バリデーション | ✅ 完了 | `.xml` / `.mxl` バリデーション実装済み |
| 3. ギター TAB 補正 | ✅ 完了 | TAB 優先 pitch 補正・チューニング・bend 保持・OCR fallback 実装済み |
| 4. パート正規化 | ✅ 完了 | `transform:role` 付与まで実装済み |
| 5. 信頼度フィルタ | ✅ 完了 | 明示的 `confidence` 属性のあるノートのみ除外 |
| 6. エントリポイント / キャッシュ | ✅ 完了 | `transform()` と品質ゲート / キャッシュ実装済み |
| 7. フィクスチャ / テスト拡充 | ✅ 完了 | unit / integration テスト通過済み |

---

## 着手条件

```text
[x] .kiro/specs/musicxml-transform/spec.json の approvals.tasks.approved が true
[x] 実装対象タスク番号が tasks.md で明確
[x] 変更に対応する unit test を先に書く
```

---

## 次のアクション

1. 実ページで Tesseract 実機確認を行い、OCR トークンと TAB ノートの対応精度を検証する
2. 必要に応じて OCR 対応付けを「パート別 / システム別 / 小節別」に強化する
3. 実装状態に合わせて `docs/DESIGN.md` と spec 追記が必要か確認する

---

## 関連ファイル

- `.kiro/specs/musicxml-transform/spec.json`
- `.kiro/specs/musicxml-transform/tasks.md`
- `.kiro/specs/musicxml-transform/design.md`
- `pipeline/transform/_transform.py`
- `pipeline/transform/guitar_fixer.py`
- `pipeline/transform/tab_ocr.py`
- `tests/unit/test_transform/test_transform.py`
- `tests/unit/test_transform/test_guitar_fixer.py`
- `tests/unit/test_transform/test_tab_ocr.py`
