"""コードラベル ↔ pitch_classes 展開（設計書 §6.3 Step3、実装指示書 T3-1）。

ラベル文字列から毎回パースさせるコストを避けるため、S3 で `pitch_classes` を
展開して `chords.json` に埋め込む（設計書 §5.2）。ラベル書式は
``<Root>:<quality>[/<bass>]`` （Harte 記法。無和音は ``"N"``）。
"""
from __future__ import annotations

from dataclasses import dataclass

NOTE_NAMES: dict[str, int] = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "F": 5, "E#": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}

# 各コード品質の音程(半音、ルートからの相対値)。大語彙対応（設計書 §6.3）。
QUALITY_INTERVALS: dict[str, tuple[int, ...]] = {
    "maj": (0, 4, 7),
    "min": (0, 3, 7),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "maj7": (0, 4, 7, 11),
    "min7": (0, 3, 7, 10),
    "7": (0, 4, 7, 10),
    "dim7": (0, 3, 6, 9),
    "hdim7": (0, 3, 6, 10),  # half-diminished (m7b5)
    "min6": (0, 3, 7, 9),
    "maj6": (0, 4, 7, 9),
    "9": (0, 4, 7, 10, 2),
    "min9": (0, 3, 7, 10, 2),
    "maj9": (0, 4, 7, 11, 2),
    "11": (0, 4, 7, 10, 2, 5),
    "13": (0, 4, 7, 10, 2, 5, 9),
    "5": (0, 7),  # パワーコード
}

# スラッシュコードのベース指定（Harte 記法のスケール度数）→ ルートからの半音。
DEGREE_SEMITONES: dict[str, int] = {
    "1": 0, "b2": 1, "2": 2, "#2": 3, "b3": 3, "3": 4, "4": 5, "#4": 6,
    "b5": 6, "5": 7, "#5": 8, "b6": 8, "6": 9, "bb7": 9, "b7": 10, "7": 11,
    "b9": 1, "9": 2, "#9": 3, "11": 5, "#11": 6, "b13": 8, "13": 9,
}


class ChordLabelError(ValueError):
    pass


@dataclass(frozen=True)
class ChordInfo:
    root: int | None
    quality: str | None
    bass: int | None
    pitch_classes: tuple[int, ...]


NO_CHORD = ChordInfo(root=None, quality=None, bass=None, pitch_classes=())


def _parse_bass(text: str, root_pc: int) -> int:
    if text in DEGREE_SEMITONES:
        return (root_pc + DEGREE_SEMITONES[text]) % 12
    if text in NOTE_NAMES:
        return NOTE_NAMES[text]
    raise ChordLabelError(f"未知のベース指定です: {text!r}")


def parse_chord_label(label: str) -> ChordInfo:
    """``"A:min7"`` / ``"D:maj/5"`` / ``"N"`` のようなラベルを展開する。"""
    if label == "N" or not label:
        return NO_CHORD

    root_part, sep, rest = label.partition(":")
    if not sep:
        # コード品質省略時は maj 扱い（例: "C" == "C:maj"）
        root_part, rest = label, "maj"

    if root_part not in NOTE_NAMES:
        raise ChordLabelError(f"未知のルート音名です: {root_part!r} (label={label!r})")
    root_pc = NOTE_NAMES[root_part]

    quality_part, slash, bass_part = rest.partition("/")
    quality_part = quality_part or "maj"
    if quality_part not in QUALITY_INTERVALS:
        raise ChordLabelError(f"未知のコード品質です: {quality_part!r} (label={label!r})")

    bass_pc = _parse_bass(bass_part, root_pc) if slash else root_pc
    pitch_classes = tuple(sorted({(root_pc + iv) % 12 for iv in QUALITY_INTERVALS[quality_part]}))

    return ChordInfo(root=root_pc, quality=quality_part, bass=bass_pc, pitch_classes=pitch_classes)
