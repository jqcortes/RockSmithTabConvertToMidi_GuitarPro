# QUALITY_SCORE.md — 品質スコア定義と計測方法

## 1. 品質スコアの目的

変換パイプラインの各ステップで品質を定量化し、
「修正不要」判定の客観的基準を提供する。

---

## 2. スコア定義

### 総合品質スコア (Overall Quality Score: OQS)

```
OQS = 0.40 × OMR_Confidence
    + 0.30 × Measure_Completeness
    + 0.15 × Pitch_Range_Validity
    + 0.15 × Part_Detection_Rate
```

### 判定基準

| OQS | 判定 | 処理 |
|---|---|---|
| ≥ 0.80 | ✅ 合格 | MIDI 出力・完了 |
| 0.60 〜 0.79 | ⚠️ 要確認 | MIDI 出力 + 警告レポート |
| < 0.60 | ❌ 失敗 | エラー終了・詳細ログ出力 |

---

## 3. 個別メトリクス

### 3-1. OMR Confidence (OMR 信頼度)

Audiveris の SIG (Symbol Interpretation Graph) に格納される
各音楽記号の認識信頼度グレード (0.0〜1.0) の加重平均。

```python
def calc_omr_confidence(musicxml_path: Path) -> float:
    """
    MusicXML の <sound> タグや Audiveris 固有拡張から
    信頼度情報を抽出して平均を計算する。
    
    Audiveris 出力の .omr ファイルから SIG グレードを直接読む方法が
    より正確だが、MusicXML 内の dynamics/tempo 要素数から
    間接的に推定する方法をフォールバックとして使用する。
    """
    ...
```

### 3-2. Measure Completeness (小節完全性)

各小節の音価合計が拍子記号に一致する割合。

```
Measure_Completeness = 正常小節数 / 全小節数
```

```python
def check_measure_completeness(score) -> float:
    errors = 0
    total = 0
    for part in score.parts:
        for measure in part.getElementsByClass('Measure'):
            total += 1
            beat_sum = sum(n.quarterLength for n in measure.notesAndRests)
            expected = measure.timeSignature.barDuration.quarterLength
            if abs(beat_sum - expected) > 0.125:  # 32分音符の誤差まで許容
                errors += 1
    return 1.0 - (errors / total) if total > 0 else 0.0
```

### 3-3. Pitch Range Validity (音域妥当性)

ギター音域 (E2=40 〜 E6=88) 内にある音符の割合。

```python
GUITAR_RANGE = (40, 88)  # MIDI ノート番号

def calc_pitch_range_validity(score, part_name: str) -> float:
    if "drum" in part_name.lower():
        return 1.0  # ドラムは音域チェック対象外
    ...
```

### 3-4. Part Detection Rate (パート検出率)

期待パート数に対する実際の検出パート数の比率。

```python
def calc_part_detection_rate(score, expected_parts: list[str]) -> float:
    detected = [p.partName for p in score.parts]
    matched = sum(
        1 for exp in expected_parts
        if any(exp.lower() in d.lower() for d in detected)
    )
    return matched / len(expected_parts)
```

---

## 4. 品質レポート形式

```json
{
  "input_file": "band_score.pdf",
  "output_midi": "band_score.mid",
  "timestamp": "2024-01-01T00:00:00Z",
  "overall_score": 0.84,
  "judgment": "PASS",
  "metrics": {
    "omr_confidence": 0.91,
    "measure_completeness": 0.97,
    "pitch_range_validity": 0.89,
    "part_detection_rate": 1.00
  },
  "warnings": [
    {
      "type": "MEASURE_INCOMPLETE",
      "location": "Part: Guitar 1, Measure: 24",
      "detail": "Expected 4.0 beats, found 3.75"
    }
  ],
  "stats": {
    "total_measures": 128,
    "total_notes": 1842,
    "processing_time_seconds": 47.3
  }
}
```

---

*最終更新: 初版生成*
