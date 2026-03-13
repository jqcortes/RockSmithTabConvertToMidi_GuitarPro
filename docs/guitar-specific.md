# guitar-specific.md — ギター特有記譜対応設計

## 1. バンドスコア特有の構成

一般的なバンドスコアのパート構成:

```
System
├── Guitar 1 (Lead)    ┐ 五線譜 + TAB 譜 (2スタッフ 1パート)
├── Guitar 2 (Rhythm)  ┘
├── Bass               │ 五線譜 + TAB 譜 (2スタッフ 1パート)
└── Drums              │ 5線譜 (打楽器記譜)
```

**重要**: ギター1パートは「五線譜 + TAB 譜」の **2スタッフ構成** であることに注意。
Audiveris は LogicalPart 機能でこれを1パートとして扱う。

---

## 2. タブ譜解析 (tab_parser.py)

### 2-1. TAB スタッフの識別

```python
def is_tab_staff(staff: Staff) -> bool:
    """
    スタッフが TAB 譜かどうかを判定する。
    
    判定基準:
    1. スタッフの線数が 6 本
    2. 'TAB' テキストが clef 位置に存在する
    3. 数字のみのノートヘッドが配置されている
    """
    return (
        staff.line_count == 6
        or staff.clef_type == "TAB"
        or has_numeric_note_heads(staff)
    )
```

### 2-2. フレット番号からピッチへの変換

```python
# ギター標準チューニング (6弦から1弦)
STANDARD_TUNING = [
    midi_pitch("E2"),  # 6弦開放 = E2 (MIDI 40)
    midi_pitch("A2"),  # 5弦開放 = A2 (MIDI 45)
    midi_pitch("D3"),  # 4弦開放 = D3 (MIDI 50)
    midi_pitch("G3"),  # 3弦開放 = G3 (MIDI 55)
    midi_pitch("B3"),  # 2弦開放 = B3 (MIDI 59)
    midi_pitch("E4"),  # 1弦開放 = E4 (MIDI 64)
]

def fret_to_pitch(string: int, fret: int, tuning=STANDARD_TUNING) -> int:
    """
    string: 1=1弦(最高音), 6=6弦(最低音)
    fret: 0=開放弦, 1-24=フレット番号
    返値: MIDI ノート番号
    """
    open_pitch = tuning[6 - string]
    return open_pitch + fret
```

### 2-3. チューニングバリアント対応

```yaml
# config/instrument_map.yaml に追加
tunings:
  standard:    [40, 45, 50, 55, 59, 64]  # EADGBe
  drop_d:      [38, 45, 50, 55, 59, 64]  # DADGBe
  open_g:      [38, 43, 50, 55, 59, 62]  # DGDGBd
  half_step_down: [39, 44, 49, 54, 58, 63]  # Eb Ab Db Gb Bb eb
```

チューニング指定がない場合は `standard` を使用。

---

## 3. ギター奏法記号の認識と変換

### 3-1. チョーキング (Bend)

**Audiveris MusicXML 出力**:
```xml
<notations>
  <technical>
    <bend>
      <bend-alter>1</bend-alter>  <!-- 半音チョーキング = 1 -->
    </bend>
  </technical>
</notations>
```

**MIDI 変換**:
```python
def bend_to_pitchbend_events(note_start, note_end, semitones):
    """
    チョーキングを Pitch Bend イベント列に変換する。
    全音チョーキング (semitones=2) を想定した標準実装。
    
    Pitch Bend 範囲: ±2半音 (デフォルト) → 8192 = 1半音
    """
    bend_events = []
    steps = 16  # 滑らかさ
    duration = note_end - note_start
    
    for i in range(steps + 1):
        t = note_start + (duration * i // steps)
        bend_value = int(8192 * semitones * i / steps)
        bend_events.append(PitchBendEvent(time=t, value=bend_value))
    
    return bend_events
```

### 3-2. ハンマリングオン / プリングオフ

```xml
<!-- MusicXML -->
<notations>
  <technical>
    <hammer-on number="1" type="start">H</hammer-on>
  </technical>
  <slur number="1" type="start"/>
</notations>
```

**MIDI 変換方針**:
- Note On velocity を 0.7 倍（ハンマリング）/ 0.6 倍（プリング）に減衰
- スラーグループ内の音符は連続して再生（ゲートタイム 100%）

### 3-3. スライド

```xml
<notations>
  <technical>
    <slide number="1" type="start" line-type="solid"/>
  </technical>
</notations>
```

**MIDI 変換**: Pitch Bend のグライドで表現
- スライドアップ: 開始音から目標音への Pitch Bend 上昇
- スライドダウン: 開始音から目標音への Pitch Bend 下降

### 3-4. パームミュート

```xml
<notations>
  <technical>
    <palm-mute>P.M.</palm-mute>
  </technical>
</notations>
```

**MIDI 変換**:
- Expression (CC#11) を 40 に設定（音量抑制）
- ゲートタイム 50% に短縮（詰まった音感）
- パームミュート終了後は CC#11 を 127 に戻す

---

## 4. ドラム記譜対応

### 4-1. GM ドラムマッピング

| 記譜位置 | 打楽器名 | GM MIDI ノート |
|---|---|---|
| ラインC5上 | Crash Cymbal 1 | 49 |
| スペースA4 | Hi-Hat (open) | 46 |
| ラインB4 | Ride Cymbal | 51 |
| ラインE5 | Hi-Hat (closed) | 42 |
| ラインE4 | Snare Drum | 38 |
| ラインC4 | Bass Drum | 36 |
| スペースA3 | Floor Tom | 41 |
| スペースF3 | Low Tom | 45 |

```yaml
# config/instrument_map.yaml
drum_map:
  # Audiveris pitch → GM note
  "C5": 49   # Crash
  "A4": 46   # Hi-Hat open
  "B4": 51   # Ride
  "E5": 42   # Hi-Hat closed
  "E4": 38   # Snare
  "C4": 36   # Kick
  "A3": 41   # Floor Tom
  "F3": 45   # Low Tom
```

---

## 5. コード記号の処理

バンドスコアには音符の上にコード記号 (`Am`, `C#m7` 等) が記載される。
Audiveris の TEXTS ステップで認識されるが、MIDI 変換では**現時点では無視**する。

将来的な拡張としてコードトラック生成を検討するが、Phase 1 対象外とする。

---

*最終更新: 初版生成*
