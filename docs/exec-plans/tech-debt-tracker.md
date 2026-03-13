# 技術的負債トラッカー — band-score-to-midi

> 優先度: 🔴高 / 🟡中 / 🟢低

---

## 未解決

### 🟡 中優先度

| # | 問題 | 影響範囲 | 推定工数 | 起票日 |
|---|---|---|---|---|

### 🟢 低優先度

| # | 問題 | 影響範囲 | 推定工数 | 起票日 |
|---|---|---|---|---|
| TD-007 | セッション終了自動化 prompt (`/session-end`) は未導入のため、exec-plan / spec 更新が手作業 | SDD 運用 | 小 | 2026-03-13 |

---

## 解決済み

| # | 問題 | 解決内容 | 解決日 |
|---|---|---|---|
| TD-R001 | `StepResult` の共通型定義が存在しない | `pipeline/common.py` に `StepResult`, `PipelineError`, `get_logger` を実装 | 2026-03-13 |
| TD-R002 | Ingest ドメインが未整備 | `pipeline/ingest/` と対応ユニットテストを実装 | 2026-03-13 |
| TD-R003 | OMR ドメインの CLI ラッパーが未整備 | `pipeline/omr/` と対応ユニットテストを実装 | 2026-03-13 |
| TD-R004 | `pipeline/render/` が未実装 | `pipeline/render/` と対応ユニットテストを実装 | 2026-03-14 |
| TD-R005 | `pipeline/quality/` が未実装 | `pipeline/quality/` と対応ユニットテストを実装 | 2026-03-14 |
| TD-R006 | `docs/` の一部ステータス表記が現実装とずれている | `AGENTS.md`, `ARCHITECTURE.md`, `.kiro/steering/structure.md` を現実装に同期 | 2026-03-13 |
| TD-R007 | `config/` の設定ファイルが不足している | `config/audiveris.properties`, `config/pipeline.yaml` を追加し、`instrument_map.yaml` を拡張。存在・構文テストを追加 | 2026-03-13 |
| TD-R008 | `tests/fixtures/` に MusicXML フィクスチャが不足している | Transform quality gate 用 4 件と Render 複数テンポ用 1 件の fixture を追加し、fixture ベースのテストへ移行 | 2026-03-13 |
