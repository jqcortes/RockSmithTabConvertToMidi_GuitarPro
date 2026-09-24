# TabForge

原曲音源（2mix）から、ギター（リード/バッキング分離）とベースの GuitarPro タブ譜
(`.gp5`) を自動生成するローカル CLI パイプライン。

詳細は `01_TabForge_詳細設計書.md` / `02_TabForge_実装指示書.md`（プロジェクト外の
指示書。このディレクトリの実装はその P0〜P4 に対応する）を参照。

## 現在の実装状態

このディレクトリは指示書の **P0〜P4** を実装したものです。

- 実装済み:
  - P0: IR スキーマ / ジョブ・キャッシュ管理 / CLI
  - P1: S0 Ingest / S1 Separate (Demucs アダプタ) / S2 Rhythm / S4 Transcribe
    アダプタ（MuScriptor / Basic Pitch, 遅延 import） / S4b Fuse / S5
    Disentangle Phase A（ベース確定） / S6 Quantize / S7 フレット割当
    （Viterbi） / S9 Export（GP5）
  - P2: チューニング/カポ推定・5弦ベース判定 / ステレオ pan 算出 / ギター
    採譜ラン (ms_gtr, bp_gtr) / `--guitar-tracks 1` 単一トラック出力
  - P3: コード認識（`ManualJsonRecognizer` 既定・`MadmomRecognizer` フォール
    バック・`LvcrDockerRecognizer` はコンテナ未構築のプレースホルダ）/
    label→pitch_classes 展開 / S5 特徴量 F1-F10 / ルールベース分類 + 2状態
    HMM 平滑化（Phase B-E） / `--guitar-tracks 2` で Lead Guitar・Rhythm
    Guitar・Bass の複数トラック出力 / リズムトラックのボイシング選択・
    ストローク生成
  - P4: 技法推定（bend/vibrato/hammer-on/slide/dead note/palm_mute（ステム
    音声のスペクトル重心を使用）、既定 OFF の harmonic/let_ring は未対応）/
    MusicXML・ASCII・MIDI・check_mix（簡易サイン波合成、fluidsynth 不使用）
    出力 / report.html（ノート数・パート内訳・警告・信頼度の低い小節一覧）
  - T3-5: `--guitar-tracks 3` 以上での複数リードトラック分割（(register,
    ioi, pan) の K-means。numpy のみで実装した簡易版）
- 未実装:
  - GuitarSet を用いた定量評価 (T2-5, データセット未取得)
  - harmonic・let_ring の高精度な判定（let_ring は既定 OFF のプレースホルダ
    のみ実装済み）
  - LVCR の実コンテナ構築（`docker/Dockerfile.chords` はプレースホルダ）
  - check_mix.wav の fluidsynth + SoundFont による本格合成（現状は減衰
    サイン波の加算合成で代替）
  - report.html のピアノロール／タブ位置ヒートマップ（テキスト情報のみ）
  - レビュー UI (P5) / 精度チューニング (P6)

## 重要な制約

`torch` / `demucs` / `basic-pitch` / `muscriptor` は `optional-dependencies.ml`
に隔離されている。これらは GPU 前提かつ MuScriptor はライセンス同意
（HuggingFace, CC BY-NC 4.0 = **非商用限定**）が必要なため、多くの開発・CI 環境
では未インストールのまま IR モデルやフレット割当などのコアロジックをテストできる
ようにしている。`engines/` 配下のアダプタは呼び出し時に初めて import するため、
未インストールでも `import tabforge` は失敗しない。実音源での end-to-end 実行
には `pip install -e ".[ml]"` と HuggingFace へのログインが必要。

## セットアップ

```bash
cd tabforge
uv sync                      # または pip install -e ".[dev]"
uv run pytest tests/unit     # 重量級 ML 依存なしで通るユニットテスト
uv run tabforge --help
```

`.[ml]` を追加インストールし、`scripts/probe_muscriptor.py` /
`scripts/probe_pyguitarpro.py` を実行して `config/instruments.yaml` の実測値
を埋めるまでは、`tabforge run` の S4 以降は実データに対して未検証。

## ライセンス

- コード: このリポジトリのライセンスに従う
- MuScriptor 重み: **CC BY-NC 4.0（非商用限定）** — 本パイプライン全体が商用利用不可になる主因
- PyGuitarPro: LGPL-3.0-only
- Demucs / Basic Pitch: MIT / Apache-2.0

生成される譜面データは原曲の著作権対象となり得る。私的利用の範囲に留め、公開・
配布する場合は権利処理を確認すること。音源・ジョブ成果物は外部送信しない。
