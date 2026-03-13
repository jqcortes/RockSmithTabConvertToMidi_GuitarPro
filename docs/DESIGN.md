# DESIGN.md — 詳細設計書

## 概要

本設計書はバンドスコア（ギター楽譜画像）を修正不要・高精度で MIDI ファイルに変換するパイプラインの詳細設計を記述する。

---

## 1. 設計方針

`docs/design-docs/core-beliefs.md` 参照。要点のみ再掲:

1. **タブ譜優先原則**: 五線譜とタブ譜が共存する場合、タブ譜のフレット情報を正として採用する
2. **無補正達成**: OMR 精度を前処理と後処理で補い、人手修正ゼロを目標とする
3. **パイプライン透明性**: 各ステップの品質スコアをログに残し、精度劣化箇所を即時特定可能にする
4. **失敗明示**: 信頼度が閾値を下回ったノートは MIDI に含めず警告レポートに記録する

---

## 2. フェーズ別設計

### Phase 1: 入力前処理 (Ingest)

**目的**: Audiveris の認識精度を最大化するための画像品質確保

#### 2-1-1. 入力フォーマット対応

| フォーマット | 処理方法 |
|---|---|
| PDF (スキャン) | `pdfplumber` / `pdf2image` で 300dpi PNG 展開 |
| PDF (デジタル) | 同上 (ベクタも同解像度でラスタライズ) |
| PNG/TIFF | そのまま前処理ステップへ |
| JPEG | 可逆変換で PNG へ変換後処理 |

#### 2-1-2. 前処理ステップ

```
1. 解像度チェック: < 300dpi → 警告、< 200dpi → 処理中断
2. グレースケール変換
3. デスキュー (傾き補正): Hough 変換で検出、最大±10度まで補正
4. ノイズ除去: Gaussian blur → Otsu 二値化
5. スタッフライン強調: モルフォロジー演算で水平線強調
6. コントラスト正規化: CLAHE (適応的ヒストグラム均等化)
7. ページ余白トリミング: 楽譜領域の自動クロップ
```

#### 2-1-3. 品質チェックゲート

前処理後に以下を満たさない場合は後続ステップを中断:
- 二値化後の黒画素比率: 5〜40%
- 検出されたスタッフライン数: ≥ 5 × (パート数の推定値)

---

### Phase 2: OMR 処理 (Audiveris)

**目的**: Audiveris CLI で楽譜を MusicXML に変換する

#### 2-2-1. Audiveris 実行設定

```properties
# config/audiveris.properties (重要設定のみ抜粋)

# タブ譜認識を有効化 (ギター TAB 対応)
org.audiveris.omr.sheet.grid.LineClusterAdapter.useTablature=true

# SIG (Symbol Interpretation Graph) の信頼度閾値
org.audiveris.omr.sig.inter.AbstractInter.minGrade=0.35

# ドラム譜認識
org.audiveris.omr.score.DrumPitchMapping.active=true

# バッチモード並列処理数 (コア数に応じて調整)
org.audiveris.omr.util.OmrExecutors.corePoolSize=4
```

#### 2-2-2. CLI 実行コマンド設計

```bash
# 基本実行パターン
audiveris \
  -batch \
  -transcribe \
  -export \
  -option org.audiveris.omr.sheet.grid.LineClusterAdapter.useTablature=true \
  -output {OUTPUT_DIR} \
  -- {INPUT_FILE}

# バンドスコア特化オプション
audiveris \
  -batch \
  -transcribe \
  -export \
  -option org.audiveris.omr.sig.inter.AbstractInter.minGrade=0.35 \
  -option org.audiveris.omr.sheet.Picture.maxShift=0.05 \
  -output {OUTPUT_DIR} \
  -- {INPUT_FILE}
```

#### 2-2-3. Audiveris パイプラインステップ対応表

| Audiveris Step | 役割 | バンドスコアでの注意点 |
|---|---|---|
| LOAD | 画像読み込み | — |
| BINARY | 二値化 | 前処理で品質確保済みのため BINARY パラメータ緩和可 |
| SCALE | スタッフ高さ推定 | マルチパート時は最小スタッフを基準にする |
| GRID | スタッフライン検出 | TAB 6線とドラム5線の混在に注意 |
| HEADERS | 小節ヘッダ解析 | 繰り返し記号・ダルセーニョ対応確認 |
| REDUCTION | 重複検出除去 | — |
| BEAMS | 連桁検出 | — |
| STEMS | 符幹検出 | — |
| HEADS | 音符頭検出 | — |
| RHYTHM | リズム解析 | ギター特有の16分音符密集部で精度低下しやすい |
| TEXTS | テキスト認識 | コード記号・歌詞の認識 (Tesseract OCR) |
| LINKS | 要素間リンク | スラー・タイの処理 |
| PAGE | ページ統合 | — |
| SCORE | スコア構築 | — |

---

### Phase 3: MusicXML 後処理 (Transform)

**目的**: Audiveris 出力の誤認識補正と MIDI 変換前の正規化

#### 2-3-1. バリデーションルール

```python
# 主要バリデーションチェック項目
VALIDATION_RULES = [
    "measure_duration_consistent",   # 各小節の音価合計が拍子記号と一致
    "note_pitch_in_guitar_range",    # ギター音域 (E2-E6) 内か確認
    "tab_staff_fret_valid",          # タブ譜フレット番号 0-24 の範囲内か
    "time_signature_present",        # 拍子記号の存在確認
    "key_signature_present",         # 調号の存在確認
    "part_count_expected",           # パート数が入力と一致するか
]
```

#### 2-3-2. ギター特化補正 (guitar_fixer.py)

| 問題 | 検出方法 | 補正方法 |
|---|---|---|
| 五線譜 pitch と TAB fret/string が矛盾 | TAB スタッフと五線譜スタッフを照合 | TAB 側の fret/string を正として `<pitch>` を上書き |
| TAB スタッフ不在 | TAB clef / 6線スタッフ不在 | 補正を行わず Audiveris 出力をそのまま維持 |
| bend / slide / palm-mute 等の技法タグ | Audiveris MusicXML の `<technical>` / `<notations>` | Transform では推定せず保持のみ行い、Render で解釈 |
| パート名や staff 構造のばらつき | `<part-list>` / clef / staff 構造を参照 | 既存構造を崩さず補助メタデータだけ付与 |

> 注意: Transform ドメインでは、Audiveris が本来担当する記号認識や画像由来の再推定（例: テキストから bend を補う、音符頭形状から harmonic を再判定する）は行わない。

#### 2-3-3. パート分離・チャンネル割り当て

```yaml
# config/instrument_map.yaml
parts:
  - name_pattern: ["Guitar", "Gt.", "Gtr", "E.Gt"]
    midi_channel: 0        # Ch.1
    midi_program: 29       # Overdriven Guitar (GM)
    transpose: -12         # ギター記譜は実音より1オクターブ高い
  
  - name_pattern: ["Bass", "Ba.", "E.Ba"]
    midi_channel: 1        # Ch.2
    midi_program: 33       # Electric Bass (finger)
    transpose: -12

  - name_pattern: ["Drums", "Dr.", "D.S"]
    midi_channel: 9        # Ch.10 (GM ドラムチャンネル固定)
    midi_program: 0        # Standard Kit

  - name_pattern: ["Keyboard", "Keys", "Piano", "Synth"]
    midi_channel: 2        # Ch.3
    midi_program: 0        # Acoustic Grand Piano
```

---

### Phase 4: MIDI 生成 (Render)

**目的**: バリデーション済み MusicXML から演奏可能な MIDI を生成する

#### 2-4-1. MIDI Type 1 構造設計

```
Track 0: テンポマップ・拍子記号・調号 (メタイベントのみ)
Track 1: Guitar Part   → Ch.1 (Program 29)
Track 2: Bass Part     → Ch.2 (Program 33)
Track 3: Drums Part    → Ch.10 (GM ドラムマッピング)
Track N: 追加パート    → Ch.N+1
```

#### 2-4-2. ギター奏法の MIDI マッピング

| 記譜記号 | MusicXML 表現 | MIDI 実装 |
|---|---|---|
| チョーキング (bend) | `<bend>` タグ | Pitch Bend CC (CC#16) でグライド |
| ハンマリングオン | `<hammer-on>` | ベロシティ低減 (×0.7) + レガート |
| プリングオフ | `<pull-off>` | ベロシティ低減 (×0.6) + レガート |
| スライド | `<slide>` | Pitch Bend で音程移動 |
| ハーモニクス | `<harmonic>` | Program 1 (Music Box) に一時切替 |
| パームミュート | `<technical><palm-mute>` | Expression CC#11 低減 + 音価短縮 |
| ビブラート | `<wavy-line>` | LFO 相当 Pitch Bend 連続送信 |

#### 2-4-3. テンポ処理

- `<metronome>` タグからテンポ抽出 (BPM)
- テンポ変動 (`<sound tempo="">`) は tempo change イベントとして挿入
- テンポ未記載の場合: デフォルト 120 BPM を使用し警告ログ出力

---

### Phase 5: 品質スコアリング (Quality)

**目的**: 変換結果の信頼度を定量化し、低品質箇所を特定する

#### 2-5-1. 品質スコア定義

`docs/QUALITY_SCORE.md` 参照。

| メトリクス | 計算方法 | 重み |
|---|---|---|
| OMR Confidence | Audiveris SIG グレード平均 | 40% |
| Measure Completeness | 拍子合計エラー率 | 30% |
| Pitch Range Validity | 音域外音符率 | 15% |
| Part Detection Rate | 期待パート数の検出率 | 15% |

総合スコア ≥ 0.80 → 合格（修正不要と判定）
総合スコア 0.60-0.79 → 要確認（警告レポート出力）
総合スコア < 0.60 → 変換失敗（エラー終了）

---

## 3. エラーハンドリング設計

`docs/RELIABILITY.md` 参照。

---

## 4. 設定ファイル階層

```
config/
├── pipeline.yaml          # パイプライン全体設定
├── audiveris.properties   # Audiveris エンジン設定
├── instrument_map.yaml    # 楽器・チャンネルマッピング
└── quality_thresholds.yaml # 品質閾値設定
```

---

*最終更新: 初版生成*
