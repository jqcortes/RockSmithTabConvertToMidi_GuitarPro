# TabForge

原曲音源（2mix）から、ギター（リード/バッキング分離）とベースの GuitarPro タブ譜
(`.gp5`) を自動生成するローカル CLI パイプライン。

詳細は `01_TabForge_詳細設計書.md` / `02_TabForge_実装指示書.md`（プロジェクト外の
指示書。このディレクトリの実装はその P0〜P1 に対応する）を参照。

## 現在の実装状態

このディレクトリは指示書の **P0（環境構築・IR・CLI骨格）+ P1（ベース単独タブの
end-to-end 骨格）** を実装したものです。

- 実装済み: IR スキーマ / ジョブ・キャッシュ管理 / CLI / S0 Ingest / S1 Separate
  (Demucs アダプタ) / S2 Rhythm / S4 Transcribe アダプタ（MuScriptor / Basic
  Pitch, 遅延 import） / S4b Fuse / S5 Disentangle（Phase A: ベースのみ）/
  S6 Quantize / S7 フレット割当（Viterbi） / S9 Export（GP5）
- 未実装（P3以降）: コード認識 (LVCR) / リード・バッキング分離の HMM 平滑化 /
  複数ギタートラック / 技法推定 / レビュー UI

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
