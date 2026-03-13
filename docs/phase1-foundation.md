# phase1-foundation.md — フェーズ1: OMR基盤構築

**ステータス**: 🟡 アクティブ  
**目標完了日**: -  
**担当**: -

---

## 目標

Audiveris CLI を使用したエンドツーエンドのパイプラインを構築し、
標準的なバンドスコア（ギター+ベース+ドラム）の MIDI 変換を実現する。

---

## 完了基準 (Definition of Done)

- [ ] `scripts/run_pipeline.sh` で PDF → MIDI のワンショット変換が動作する
- [ ] テスト用バンドスコア3枚で品質スコア ≥ 0.80 を達成
- [ ] `docs/QUALITY_SCORE.md` のメトリクスが全て計測可能
- [ ] 単体テストカバレッジ ≥ 70%

---

## タスクリスト

### T1-01: 環境セットアップ
- [ ] Java 17 インストール確認スクリプト作成
- [ ] Audiveris 最新リリースの自動ダウンロードスクリプト
- [ ] Python 依存関係 `requirements.txt` 作成
- [ ] Docker コンテナ定義 (`Dockerfile`)

### T1-02: Ingest 層実装
- [ ] `pipeline/ingest/image_loader.py` 実装
  - PDF → PNG 変換 (pdf2image)
  - 解像度チェック (< 300dpi で警告)
- [ ] `pipeline/ingest/preprocessor.py` 実装
  - グレースケール変換
  - デスキュー (OpenCV Hough)
  - Otsu 二値化
  - CLAHE コントラスト正規化
- [ ] 前処理の単体テスト作成

### T1-03: OMR 層実装
- [ ] `pipeline/omr/audiveris_runner.py` 実装
  - subprocess ラッパー
  - タイムアウト処理 (300秒)
  - 標準出力・エラー出力のキャプチャ
- [ ] `pipeline/omr/config_builder.py` 実装
  - デフォルト設定生成
  - バンドスコア特化設定
- [ ] OMR 層の統合テスト作成（テスト用スコア使用）

### T1-04: Transform 層実装
- [ ] `pipeline/transform/musicxml_validator.py` 実装
  - lxml によるスキーマ検証
  - 拍子合計チェック
  - 音域チェック
- [ ] `pipeline/transform/guitar_fixer.py` 実装
  - オクターブ補正
  - TAB フレット値検証
- [ ] `pipeline/transform/part_splitter.py` 実装
  - `config/instrument_map.yaml` に基づくパート識別
  - チャンネル割り当て

### T1-05: Render 層実装
- [ ] `pipeline/render/midi_renderer.py` 実装 (music21 使用)
  - MusicXML → MIDI Type 1
  - テンポマップ生成
- [ ] `pipeline/render/channel_mapper.py` 実装
  - GM チャンネル割り当て
  - Program Change 挿入
- [ ] MIDI 出力の聴感テスト

### T1-06: Quality 層実装
- [ ] `pipeline/quality/scorer.py` 実装
- [ ] `pipeline/quality/reporter.py` 実装 (JSON レポート生成)
- [ ] `scripts/run_pipeline.sh` 統合スクリプト作成

### T1-07: ドキュメント整備
- [ ] `docs/FRONTEND.md` CLI 使用方法記述
- [ ] `docs/references/audiveris-cli-reference.md` 作成
- [ ] README.md (プロジェクト直下) 作成

---

## リスクと対策

| リスク | 影響度 | 対策 |
|---|---|---|
| Audiveris が TAB 6線を正しく認識できない | 高 | `useTablature=true` + 前処理強化 |
| 手書き・低解像度スコアでの精度低下 | 中 | 最低解像度ゲートで早期リジェクト |
| music21 の MIDI 出力でチャンネル割り当てが崩れる | 中 | mido で低レベル MIDI 操作にフォールバック |

---

*最終更新: 初版生成*
