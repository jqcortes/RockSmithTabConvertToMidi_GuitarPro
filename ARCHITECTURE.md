# ARCHITECTURE.md — ドメインとパッケージ階層マップ

## 1. システム全体アーキテクチャ

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                               band-score-to-midi                                  │
├─────────────┬──────────────┬──────────────┬────────────────────┬──────────────────┤
│ 入力ドメイン  │ OMR ドメイン   │ 変換ドメイン   │ 出力ドメイン         │ 品質ドメイン       │
│ (Ingest)    │ (Recognize)  │ (Transform)  │ (Render)           │ (Quality)        │
├─────────────┼──────────────┼──────────────┼────────────────────┼──────────────────┤
│ PDF/PNG      │ Audiveris    │ MusicXML     │ MIDI Type 1         │ quality_report   │
│ スキャン画像  │ CLI wrapper  │ 補正・分離      │ per-channel         │ score / judgment │
│ 前処理        │ XML export   │ quality gate │ tempo/instrument    │ warnings         │
└─────────────┴──────────────┴──────────────┴────────────────────┴──────────────────┘
       ↓               ↓              ↓                 ↓                   ↓
   image_in/       omr_engine/    xml_processor/      midi_out/        quality_out/
```

---

## 2. パッケージ階層

```
band-score-to-midi/
├── AGENTS.md                    # エージェント目次
├── ARCHITECTURE.md              # 本ファイル
├── pyproject.toml               # 依存関係・CLI エントリポイント定義
├── docs/                        # 全ドキュメント
│   ├── DESIGN.md
│   ├── FRONTEND.md
│   ├── QUALITY_SCORE.md
│   ├── SPEC_DRIVEN_DEV_GUIDE.md
│   ├── audiveris-cli-reference.md
│   ├── guitar-specific.md
│   ├── omr-pipeline.md
│   ├── phase1-foundation.md
│   ├── design-docs/
│   ├── exec-plans/
│   └── generated/
├── pipeline/                    # 実装コア
│   ├── __init__.py
│   ├── __main__.py              # CLI (`convert`, `quality`)
│   ├── common.py                # StepResult / PipelineError / logger
│   ├── ingest/                  # 入力ドメイン
│   │   ├── __init__.py
│   │   ├── image_loader.py      # PDF/PNG ローダー
│   │   ├── preprocessor.py      # 画像前処理 (deskew/denoise)
│   │   └── validator.py         # 入力検証
│   ├── omr/                     # OMR ドメイン
│   │   ├── __init__.py
│   │   ├── _transcribe.py       # ドメインエントリポイント
│   │   ├── config.py            # 設定解決
│   │   ├── engine.py            # Java / JAR 検証
│   │   ├── finder.py            # 出力探索
│   │   ├── runner.py            # CLI 実行
│   │   └── errors.py            # 例外階層
│   ├── transform/               # 変換ドメイン
│   │   ├── __init__.py
│   │   ├── _transform.py        # quality gate 付き変換オーケストレーション
│   │   ├── validator.py         # MusicXML 検証
│   │   ├── guitar_fixer.py      # ギター特有補正
│   │   ├── part_identifier.py   # パート識別
│   │   ├── confidence_filter.py # 信頼度フィルタ
│   │   └── errors.py            # 例外階層
│   ├── render/                  # 出力ドメイン
│   │   ├── __init__.py
│   │   ├── _render.py           # render エントリポイント
│   │   ├── midi_renderer.py     # MusicXML → MIDI
│   │   ├── channel_mapper.py    # GM チャンネルマッピング
│   │   ├── tempo_resolver.py    # テンポ解決
│   │   ├── technique_renderer.py# ギター奏法 MIDI 反映
│   │   └── errors.py            # 例外階層
│   └── quality/                 # 品質ドメイン
│       ├── __init__.py
│       ├── _score.py            # score エントリポイント
│       ├── validator.py         # 入力検証
│       ├── metrics.py           # メトリクス計算
│       ├── judge.py             # weighted judgment
│       ├── reporter.py          # レポート生成
│       └── errors.py            # 例外階層
├── config/
│   └── instrument_map.yaml      # 楽器→MIDI チャンネルマップ
├── tests/
│   ├── fixtures/                # テスト用バンドスコアサンプル
│   ├── unit/
│   └── integration/
└── scripts/
    └── create_fixtures.py       # フィクスチャ生成補助
```

---

## 3. データフロー

```
入力画像/PDF
    │
    ▼
[Ingest] image_loader → preprocessor → validator
    │  出力: 前処理済み高解像度 PNG (300dpi+)
    │
    ▼
[OMR] audiveris_runner (CLI: -batch -transcribe -export)
    │  出力: MusicXML (.mxl / .xml)
    │
    ▼
[Transform] musicxml_validator → guitar_fixer → part_splitter
    │  出力: quality gate を通過した補正済み MusicXML
    │
    ▼
[Render] midi_renderer → channel_mapper → tempo_resolver → technique_renderer
    │  出力: MIDI Type 1 (.mid)
    │
    ▼
[Quality] metrics → judge → reporter
       出力: quality_report.json
```

---

## 4. 外部依存関係

| 依存 | バージョン | 用途 |
|---|---|---|
| Audiveris | 5.3+ | OMR エンジン |
| Java | 17+ | Audiveris 実行環境 |
| Python | 3.11+ | パイプライン制御 |
| music21 | 9.x | MusicXML/MIDI 操作 |
| opencv-python | 4.x | 画像前処理 |
| pillow | 10.x | 画像入出力 |
| lxml | 4.x | MusicXML パース |
| mido | 1.x | 低レベル MIDI 操作 |

---

## 5. ドメイン間インターフェース規約

- 各ドメインは **ファイルパス文字列** を入出力とする（疎結合）
- エラーは `PipelineError` 基底クラスを継承した例外で伝播
- 各ステップは `StepResult(success, output_path, metrics, warnings)` を返す
- ログは構造化 JSON ログ (structlog) で統一
- CLI は `pipeline.__main__` に集約し、`convert` と `quality` の 2 サブコマンドを提供する

---

*最終更新: 2026-03-13 実装状態同期*
