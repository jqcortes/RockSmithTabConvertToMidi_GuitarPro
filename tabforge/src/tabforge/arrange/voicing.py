"""リズムトラックのボイシング選択（設計書 §9.4、実装指示書 T3-4）。

「LVCR のコードネーム」＋「実際に鳴っていたノート」の両方から決める。
ラベルだけでボイシングを決めると原曲と違う押さえ方になるため、`sounding`
（S5 で rhythm 判定された実発音ノート）とのピッチクラス一致度で選ぶ。
"""
from __future__ import annotations

from dataclasses import dataclass

from tabforge.ir.models import ChordSegment, GridIR, Note

PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass(frozen=True)
class Shape:
    """具体的なフレット番号（絶対値）。index0 = 1弦（最高音）、None = ミュート。"""

    name: str
    root_pc: int
    quality: str
    frets: tuple[int | None, ...]


def _transpose(base: tuple[int | None, ...], offset: int) -> tuple[int | None, ...]:
    return tuple(f + offset if f is not None else None for f in base)


# 定型シェイプライブラリ（設計書 §9.4）。index0 = 1弦（最高音）。
OPEN_SHAPES: dict[tuple[int, str], tuple[int | None, ...]] = {
    (4, "maj"): (0, 0, 1, 2, 2, 0),          # E
    (9, "maj"): (0, 2, 2, 2, 0, None),       # A
    (2, "maj"): (2, 3, 2, 0, None, None),    # D
    (7, "maj"): (3, 0, 0, 0, 2, 3),          # G
    (0, "maj"): (0, 1, 0, 2, 3, None),       # C
    (9, "min"): (0, 1, 2, 2, 0, None),       # Am
    (4, "min"): (0, 0, 0, 2, 2, 0),          # Em
    (2, "min"): (1, 3, 2, 0, None, None),    # Dm
    (5, "maj"): (1, 1, 2, 3, 3, 1),          # F（Eシェイプ・バレー基準形）
}

# バレー(movable)シェイプの基準形（ルートをフレット0とした相対値）。
E_SHAPE_MAJ_BASE: tuple[int | None, ...] = (0, 0, 1, 2, 2, 0)
E_SHAPE_MIN_BASE: tuple[int | None, ...] = (0, 0, 0, 2, 2, 0)
A_SHAPE_MAJ_BASE: tuple[int | None, ...] = (0, 2, 2, 2, 0, None)
A_SHAPE_MIN_BASE: tuple[int | None, ...] = (0, 1, 2, 2, 0, None)

# パワーコード基準形（ルート弦=6弦(index5) or 5弦(index4)、フレット0=ルート）。
POWER_E_BASE: tuple[int | None, ...] = (None, None, None, None, 2, 0)
POWER_E_OCTAVE_BASE: tuple[int | None, ...] = (None, None, None, 2, 2, 0)
POWER_A_BASE: tuple[int | None, ...] = (None, None, None, 2, 0, None)
POWER_A_OCTAVE_BASE: tuple[int | None, ...] = (None, None, 2, 2, 0, None)

MAX_USABLE_FRET = 15


def _quality_bucket(quality: str | None) -> str:
    """barre シェイプは maj/min の2種類しか持たないため、拡張コードを近似する。"""
    if quality is None:
        return "maj"
    return "min" if quality.startswith("min") else "maj"


def _barre_shape(root_pc: int, quality: str, root_string: int, tuning: tuple[int, ...]) -> Shape | None:
    bucket = _quality_bucket(quality)
    if root_string == 5:
        base = E_SHAPE_MAJ_BASE if bucket == "maj" else E_SHAPE_MIN_BASE
    else:
        base = A_SHAPE_MAJ_BASE if bucket == "maj" else A_SHAPE_MIN_BASE
    root_open_pc = tuning[root_string] % 12
    offset = (root_pc - root_open_pc) % 12
    if offset > MAX_USABLE_FRET:
        return None
    name = f"{PITCH_NAMES[root_pc]}{bucket}(barre)"
    return Shape(name=name, root_pc=root_pc, quality=quality, frets=_transpose(base, offset))


def _power_shape(root_pc: int, tuning: tuple[int, ...], octave: bool, root_string: int = 5) -> Shape:
    if root_string == 5:
        base = POWER_E_OCTAVE_BASE if octave else POWER_E_BASE
    else:
        base = POWER_A_OCTAVE_BASE if octave else POWER_A_BASE
    root_open_pc = tuning[root_string] % 12
    offset = (root_pc - root_open_pc) % 12
    return Shape(name=f"{PITCH_NAMES[root_pc]}5", root_pc=root_pc, quality="5", frets=_transpose(base, offset))


def classify_chord_form(pitch_classes: list[int]) -> str:
    """1. 形態判定（設計書 §9.4）: パワーコード / トライアド・セブンス / 拡張。"""
    n = len(set(pitch_classes))
    if n <= 2:
        return "power"
    if n <= 4:
        return "basic"
    return "extended"


def generate_candidates(chord: ChordSegment, tuning: tuple[int, ...]) -> list[Shape]:
    """2. ボイシング候補生成: root/quality/bass に一致するシェイプを列挙する。"""
    if chord.root is None:
        return []
    candidates: list[Shape] = []
    key = (chord.root, chord.quality)
    is_root_position = chord.bass is None or chord.bass == chord.root

    if key in OPEN_SHAPES and is_root_position:
        candidates.append(Shape(name="open", root_pc=chord.root, quality=chord.quality or "maj",
                                 frets=OPEN_SHAPES[key]))

    form = classify_chord_form(chord.pitch_classes)
    if form == "power" or chord.quality == "5":
        candidates.append(_power_shape(chord.root, tuning, octave=False, root_string=5))
        candidates.append(_power_shape(chord.root, tuning, octave=True, root_string=5))
        candidates.append(_power_shape(chord.root, tuning, octave=False, root_string=4))
    else:
        for root_string in (5, 4):
            shape = _barre_shape(chord.root, chord.quality or "maj", root_string, tuning)
            if shape is not None:
                candidates.append(shape)

    return [c for c in candidates if c is not None]


def _shape_pitch_classes(shape: Shape, tuning: tuple[int, ...]) -> set[int]:
    return {(tuning[i] + fret) % 12 for i, fret in enumerate(shape.frets) if fret is not None}


def _position(shape: Shape) -> float:
    frets = [f for f in shape.frets if f is not None and f > 0]
    return sum(frets) / len(frets) if frets else 0.0


def select_voicing(
    chord: ChordSegment, sounding: list[Note], prev: Shape | None, tuning: tuple[int, ...]
) -> Shape | None:
    """3. 各候補に「P との pitch 集合一致度」＋「直前ボイシングからのポジション移動量」でスコア付け。"""
    candidates = generate_candidates(chord, tuning)
    if not candidates:
        return None

    sounding_pcs = {n.pitch % 12 for n in sounding} if sounding else set(chord.pitch_classes)

    def score(shape: Shape) -> float:
        pcs = _shape_pitch_classes(shape, tuning)
        match = len(pcs & sounding_pcs) / max(1, len(sounding_pcs))
        move_penalty = 0.05 * abs(_position(shape) - _position(prev)) if prev is not None else 0.0
        return match - move_penalty

    return max(candidates, key=score)


@dataclass(frozen=True)
class StrumBeat:
    time: float
    stroke: str  # "down" | "up"


def generate_strumming(rhythm_notes: list[Note], grid: GridIR, subdivisions: int = 2) -> list[StrumBeat]:
    """5. オンセット密度から表拍=down / 裏拍=up のストロークを生成する。

    `subdivisions` は1拍あたりの分割数（既定2 = 8分音符グリッド。16分は4を指定）。
    """
    if not rhythm_notes or not grid.beats:
        return []

    beat_times = [b.t for b in grid.beats]
    onsets = sorted({round(n.onset, 4) for n in rhythm_notes})

    strokes: list[StrumBeat] = []
    for t in onsets:
        i = 0
        while i + 1 < len(beat_times) and beat_times[i + 1] <= t:
            i += 1
        beat_start = beat_times[i]
        beat_end = beat_times[i + 1] if i + 1 < len(beat_times) else beat_start + (
            beat_times[i] - beat_times[i - 1] if i > 0 else 0.5
        )
        beat_len = beat_end - beat_start
        frac = (t - beat_start) / beat_len if beat_len > 0 else 0.0
        subdivision_index = round(frac * subdivisions)
        stroke = "down" if subdivision_index % 2 == 0 else "up"
        strokes.append(StrumBeat(time=t, stroke=stroke))

    return strokes
