"""S8 技法推定（設計書 §9.5、実装指示書 T4-1 / T4-2）。

MuScriptor は技法情報を一切出さないため、Basic Pitch のベンド曲線
(`Note.bend_curve`) とノート間のタイミング・フレット関係から推定する。

**設計上の簡略化**: 本来 S8 は tab.json 確定後の独立ステージだが、
Hammer-on/Pull-off・Slide の判定には「元の Note（onset/offset/pitch）」と
「S7 で割り当てられた具体的な (string, fret)」の両方が必要になる。
tab.json は tick 表現のみで秒レベルの onset/offset を保持しないため、
本実装では `arrange.fretting` の Viterbi 実行前後にフックする形で
`stages/s7_arrange.build_track` から本モジュールの関数を呼び出す
（T4-2: legato 候補を `OnsetGroup.legato_links` に渡して Viterbi 側で
同一弦維持を強制し、確定後に実際の fret 差で確認する二段階判定）。

**方針**: 確信度が低い技法は付けない（誤検出は人手修正コストを増やす）。
palm_mute・harmonic はスペクトル解析（音響特徴）が必要で、この段階では
音声を直接扱わないため既定 OFF のプレースホルダとする。
"""
from __future__ import annotations

from itertools import pairwise

from tabforge.config import TechniqueConfig
from tabforge.ir.models import BendEffect, Note, NoteEffects

HAMMER_MAX_DT_BEATS = 0.25
HAMMER_MAX_FRET_DIFF = 3
SLIDE_MAX_DT_BEATS = 0.5
SLIDE_MIN_FRET_DIFF = 1
SLIDE_MAX_FRET_DIFF = 4
DEAD_NOTE_MAX_DUR_SEC = 0.06
VIBRATO_MIN_AMPLITUDE = 0.2
VIBRATO_MAX_AMPLITUDE = 0.6
VIBRATO_MIN_HZ = 4.0
VIBRATO_MAX_HZ = 8.0
LEGATO_CANDIDATE_MAX_PITCH_DIFF = 5  # フレット差<=3 の粗い近似（弦未確定の事前判定）


def infer_bend(note: Note, cfg: TechniqueConfig) -> BendEffect | None:
    """bend_curve の最大偏差 >= bend_min_semitone、かつ立ち上がりが後半 → BendEffect。"""
    if not cfg.enabled.get("bend", True) or not note.bend_curve:
        return None
    max_pos, max_val = max(note.bend_curve, key=lambda pv: abs(pv[1]))
    if abs(max_val) < cfg.bend_min_semitone:
        return None
    if max_pos < 0.5:  # 立ち上がりが前半 = チョーキングではなく別の表現の可能性
        return None
    points = [(round(pos * 12), round(val * 4)) for pos, val in note.bend_curve]
    return BendEffect(points=points)


def infer_vibrato(note: Note, cfg: TechniqueConfig) -> bool:
    """bend_curve に 4-8Hz の周期変動、振幅 0.2-0.6半音 → vibrato=True。"""
    if not cfg.enabled.get("vibrato", True) or not note.bend_curve or len(note.bend_curve) < 6:
        return False
    values = [v for _pos, v in note.bend_curve]
    amplitude = (max(values) - min(values)) / 2
    if not (VIBRATO_MIN_AMPLITUDE <= amplitude <= VIBRATO_MAX_AMPLITUDE):
        return False
    duration = note.offset - note.onset
    if duration <= 0:
        return False
    mean_v = sum(values) / len(values)
    crossings = sum(1 for a, b in pairwise(values) if (a - mean_v) * (b - mean_v) < 0)
    freq_hz = (crossings / 2) / duration
    return VIBRATO_MIN_HZ <= freq_hz <= VIBRATO_MAX_HZ


def is_legato_candidate(prev: Note, cur: Note, dt_beats: float) -> bool:
    """Viterbi 実行前の事前判定（弦がまだ確定していないため pitch 差で近似する）。

    T4-2: この候補を `OnsetGroup.legato_links` に渡し、Viterbi 側で
    同一弦維持を強制する（成立しなければ制約を緩めて通常割当に戻る）。
    """
    return dt_beats < SLIDE_MAX_DT_BEATS and abs(cur.pitch - prev.pitch) <= LEGATO_CANDIDATE_MAX_PITCH_DIFF


def confirm_hammer_or_slide(
    dt_beats: float, fret_diff: int, same_string: bool, cfg: TechniqueConfig
) -> tuple[bool, str | None]:
    """Viterbi 確定後、実際の (string, fret) 差から HO/PO・スライドを確定する。

    戻り値: (hammer, slide_type)。同時に true にはならない。
    """
    if not same_string or fret_diff == 0:
        return False, None
    abs_diff = abs(fret_diff)
    if cfg.enabled.get("hammer", True) and dt_beats < HAMMER_MAX_DT_BEATS and abs_diff <= HAMMER_MAX_FRET_DIFF:
        return True, None
    if (
        cfg.enabled.get("slide", True)
        and dt_beats < SLIDE_MAX_DT_BEATS
        and SLIDE_MIN_FRET_DIFF <= abs_diff <= SLIDE_MAX_FRET_DIFF
    ):
        return False, "shiftSlideTo"
    return False, None


def infer_dead_note(note: Note, cfg: TechniqueConfig) -> bool:
    """音長 < 60ms → デッドノート（NoteType.dead）。"""
    if not cfg.enabled.get("dead", True):
        return False
    return (note.offset - note.onset) < DEAD_NOTE_MAX_DUR_SEC


def infer_let_ring(note: Note, next_note: Note | None, cfg: TechniqueConfig) -> bool:
    """連続するアルペジオで offset が次のオンセットを超えて重なる → let_ring=True。"""
    if not cfg.enabled.get("let_ring", False) or next_note is None:
        return False
    return note.offset > next_note.onset


def build_note_effects(
    note: Note,
    next_note: Note | None,
    hammer: bool,
    slide: str | None,
    cfg: TechniqueConfig,
) -> NoteEffects:
    return NoteEffects(
        bend=infer_bend(note, cfg),
        vibrato=infer_vibrato(note, cfg),
        hammer=hammer,
        slide=slide,
        palm_mute=False,  # 要音声解析。P4 のこの実装では未対応（誤検出防止のため既定 False）
        dead=infer_dead_note(note, cfg),
        let_ring=infer_let_ring(note, next_note, cfg),
        harmonic=False,  # 既定 OFF（誤検出多、設計書 §9.5）
    )
