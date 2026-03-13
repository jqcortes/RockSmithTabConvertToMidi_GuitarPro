# omr-pipeline.md — Audiveris OMR パイプライン詳細設計

## 1. Audiveris アーキテクチャ概要

Audiveris は内部的に以下のデータモデルを使用する:

- **Book**: 1つの楽譜ファイル全体（複数 Sheet を含む）
- **Sheet**: 楽譜の1ページ
- **System**: ページ内の1段（全パートの横断）
- **Part**: 特定楽器のパート（スタッフセット）
- **Measure**: 小節
- **SIG (Symbol Interpretation Graph)**: 認識された音楽記号とその関係グラフ

---

## 2. CLI ラッパー設計 (audiveris_runner.py)

```python
class AudiverisRunner:
    """
    Audiveris CLI のラッパー。
    プロセスを subprocess で制御し、タイムアウト・エラーを管理する。
    """
    
    DEFAULT_OPTIONS = {
        # タブ譜認識
        "org.audiveris.omr.sheet.grid.LineClusterAdapter.useTablature": "true",
        # 最低信頼度閾値（低くするほど認識数増えるが誤認識も増える）
        "org.audiveris.omr.sig.inter.AbstractInter.minGrade": "0.35",
        # ページシフト許容量（歪み補正）
        "org.audiveris.omr.sheet.Picture.maxShift": "0.05",
    }
    
    def run(
        self,
        input_path: Path,
        output_dir: Path,
        options: dict | None = None,
        timeout_seconds: int = 300,
    ) -> StepResult:
        ...
    
    def _build_command(self, input_path, output_dir, options) -> list[str]:
        cmd = [
            "audiveris",
            "-batch",
            "-transcribe",
            "-export",
        ]
        merged = {**self.DEFAULT_OPTIONS, **(options or {})}
        for k, v in merged.items():
            cmd += ["-option", f"{k}={v}"]
        cmd += ["-output", str(output_dir)]
        cmd += ["--", str(input_path)]
        return cmd
```

---

## 3. Audiveris ステップ別チューニング方針

### BINARY (二値化)

- 前処理で品質確保済みのため、`GLOBAL` モードより `LOCAL` (adaptive) が安定
- 設定: `org.audiveris.omr.sheet.picture.PictureFactory.binarizationFilter=GLOBAL`
- スキャン品質が低い場合は `ADAPTIVE` に切り替え

### GRID (スタッフ検出)

バンドスコアで最も問題が発生しやすいステップ。

**問題**: ドラムスタッフ(5線)・ギタータブスタッフ(6線)が混在する場合、
6線スタッフを検出できないケースがある。

**対策**:
```properties
# 6線スタッフ (TAB) を有効化
org.audiveris.omr.grid.BarsRetriever.minStaffCount=5
org.audiveris.omr.grid.BarsRetriever.maxStaffCount=6
```

### RHYTHM (リズム解析)

**問題**: ギターの密集アルペジオ (16分音符以下) で音価算出が狂うケースがある。

**対策**: バリデーションフェーズで拍子合計チェックを行い、
不整合小節は警告として記録する（自動補正はしない）。

### TEXTS (テキスト認識)

- Tesseract OCR を使用
- コード記号 (`Am`, `G#m7` 等) は `eng` 言語モデルで認識
- 日本語楽譜の場合は `jpn+eng` を指定

```bash
# OCR 言語設定
-option org.audiveris.omr.text.tesseract.TesseractOCR.language=eng
```

---

## 4. マルチページ処理

```
PDF (複数ページ)
    │
    ├── Page 1 → Sheet 1 → OMR → MusicXML Part 1
    ├── Page 2 → Sheet 2 → OMR → MusicXML Part 2
    └── Page N → Sheet N → OMR → MusicXML Part N
              │
              └── [merge] → 統合 MusicXML → MIDI
```

Audiveris は複数ページPDFを1つのBookとして扱い、
Sheet間の小節接続を自動処理する。

---

## 5. エラーケースと対応

| エラー | 発生条件 | 対応 |
|---|---|---|
| `StaffNotFoundException` | スタッフが検出できない | 前処理パラメータ強化して再試行 |
| `MeasureSplitException` | 小節境界が不明瞭 | 画像解像度確認・手動バーライン指定 |
| タイムアウト | 処理時間 > 300s | `corePoolSize` 増加または画像分割 |
| メモリ不足 | 大判スコア | ページ単位に分割して処理 |

---

*最終更新: 初版生成*
