# musicxml-transform: Transform ドメインの仕様駆動実装

**ステータス**: 進行中  
**優先度**: 🔴 高  
**担当**: -  
**起票日**: 2026-03-13  

---

## 概要

`musicxml-transform` spec に基づいて、Transform ドメインの
MusicXML 検証・品質ゲート判定・条件付き TAB 補正・パート正規化・信頼度フィルタ・エントリポイントを
TDD で段階的に実装する。

現状、`.kiro/specs/musicxml-transform/` は requirements / design / tasks まで揃っており、
`pipeline/transform/errors.py` と `tests/unit/test_transform/test_errors.py` は先行着手済み。

---

## フェーズ分解

| タスク | 状態 | 説明 |
|---|---|---|
| 1. 例外階層 | 🟡 着手済み | `pipeline/transform/errors.py` と対応テストが存在 |
| 2. MusicXML バリデーション | ⬜ 未着手 | `.xml` / `.mxl` の検証ロジックを追加 |
| 3. ギター TAB 補正 | ⬜ 未着手 | 品質ゲート不合格時だけ pitch 上書き・チューニング読込・ bend 保持 |
| 4. パート正規化 | ⬜ 未着手 | Audiveris の既存 part 構造を保ったまま補助メタデータ付与 |
| 5. 信頼度フィルタ | ⬜ 未着手 | 明示的 `confidence` 属性がある場合だけ除外 |
| 6. エントリポイント / キャッシュ | ⬜ 未着手 | `transform()`、品質ゲート、条件付き fallback 組み上げ |
| 7. フィクスチャ / テスト拡充 | ⬜ 未着手 | MusicXML fixture と unit test を整備 |

---

## 着手条件

```text
[ ] .kiro/specs/musicxml-transform/spec.json の approvals.tasks.approved が true
[ ] 実装対象タスク番号が tasks.md で明確
[ ] 変更に対応する unit test を先に書く
```

---

## 次のアクション

1. `/kiro-spec-status musicxml-transform` で現在状態を確認する
2. タスク未承認なら `/kiro-spec-tasks musicxml-transform` でレビュー後に承認する
3. 承認後に `/kiro-spec-impl musicxml-transform 6.1` で品質ゲート付き fallback 制御から着手する

---

## 関連ファイル

- `.kiro/specs/musicxml-transform/spec.json`
- `.kiro/specs/musicxml-transform/tasks.md`
- `.kiro/specs/musicxml-transform/design.md`
- `pipeline/transform/errors.py`
- `tests/unit/test_transform/test_errors.py`
