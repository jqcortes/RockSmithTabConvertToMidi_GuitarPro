# midi-render: Render ドメインの仕様駆動実装

**ステータス**: 完了  
**優先度**: 🔴 高  
**担当**: -  
**起票日**: 2026-03-13

---

## 概要

`midi-render` spec に基づいて、Render ドメインの
MIDI Type 1 出力・チャンネル割り当て・テンポ処理・ギター奏法変換・キャッシュ制御を
TDD で段階的に実装する。

Render ドメインの主要構成要素は実装済みであり、
Transform 後の MusicXML から MIDI Type 1 を生成できる状態になった。

---

## フェーズ分解

| タスク | 状態 | 説明 |
|---|---|---|
| 1. 例外階層 | ✅ 完了 | `RenderError` / `RenderValidationError` / `RenderExecutionError` |
| 2. チャンネル割り当て | ✅ 完了 | guitar / bass / drums / other のマッピング |
| 3. テンポ / メタトラック | ✅ 完了 | Track 0 と tempo change の構築 |
| 4. MIDI レンダラ本体 | ✅ 完了 | MusicXML → MIDI Type 1 |
| 5. 奏法レンダリング | ✅ 完了 | bend / slide / palm-mute / hammer-on / pull-off |
| 6. エントリポイント / キャッシュ | ✅ 完了 | `render()` 公開 API |
| 7. フィクスチャ / テスト | ✅ 完了 | Render 専用 fixture と unit test |

---

## 着手条件

```text
[x] .kiro/specs/midi-render/spec.json の approvals.tasks.approved が true
[x] 実装対象タスク番号が tasks.md で明確
[x] 変更に対応する unit test を先に書く
```

---

## 次のアクション

1. Quality ドメイン spec を起こす
2. Render の統合テストを追加する
3. CLI から Render ステップを配線する

---

## 関連ファイル

- `.kiro/specs/midi-render/spec.json`
- `.kiro/specs/midi-render/requirements.md`
- `.kiro/specs/midi-render/design.md`
- `.kiro/specs/midi-render/tasks.md`
- `docs/DESIGN.md`
- `docs/guitar-specific.md`