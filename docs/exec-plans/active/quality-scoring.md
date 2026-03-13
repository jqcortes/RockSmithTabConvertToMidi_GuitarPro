# quality-scoring: Quality ドメインの仕様駆動実装

**ステータス**: 完了  
**優先度**: 🔴 高  
**担当**: -  
**起票日**: 2026-03-14

---

## 概要

`quality-scoring` spec に基づいて、Quality ドメインの
品質メトリクス算出・総合スコア判定・JSON レポート出力・キャッシュ制御を
TDD で段階的に実装する。

Quality ドメインの主要構成要素は実装済みであり、
Transform 済み MusicXML と MIDI から `quality_report.json` を生成できる状態になった。

---

## フェーズ分解

| タスク | 状態 | 説明 |
|---|---|---|
| 1. 例外階層 | ✅ 完了 | `QualityError` / `QualityValidationError` / `QualityExecutionError` |
| 2. 入力検証 | ✅ 完了 | MusicXML / MIDI の存在確認と読み込み検証 |
| 3. メトリクス計算 | ✅ 完了 | 4 指標と warnings / stats の生成 |
| 4. 総合スコア判定 | ✅ 完了 | PASS / REVIEW / FAIL |
| 5. JSON レポート生成 | ✅ 完了 | `quality_report.json` 出力 |
| 6. エントリポイント / キャッシュ | ✅ 完了 | `score()` 公開 API |
| 7. フィクスチャ / テスト | ✅ 完了 | Quality 専用 fixture と unit test |

---

## 着手条件

```text
[x] .kiro/specs/quality-scoring/spec.json の approvals.tasks.approved が true
[x] 実装対象タスク番号が tasks.md で明確
[x] 変更に対応する unit test を先に書く
```

---

## 次のアクション

1. CLI から Quality ステップを配線する
2. 統合テストを追加する
3. stale ドキュメントを実装状態へ同期する

---

## 関連ファイル

- `.kiro/specs/quality-scoring/spec.json`
- `.kiro/specs/quality-scoring/requirements.md`
- `.kiro/specs/quality-scoring/design.md`
- `.kiro/specs/quality-scoring/tasks.md`
- `docs/QUALITY_SCORE.md`
- `docs/DESIGN.md`