"""S6 Quantize & Cleanup（設計書 §9.1、実装指示書 T1-7）。

グリッド吸着・音価の GP Duration 量子化・ゴースト除去・最小音価保証を行う。
同弦重複の解消は S7 に委譲し、ここでは同一 pitch の完全重複のみマージする。
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass

from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import Beat, GridIR, Note, NotesIR
from tabforge.job import Job
from tabforge.theory.duration import duration_ticks, quantize_to_gp_durations

PPQ = 480  # ticks per quarter note
MIN_NOTE_VALUE = 32  # 最小音価保証: 32分未満は32分に丸める


def _local_beat_window(t: float, beats: list[Beat]) -> tuple[float, float] | None:
    if len(beats) < 2:
        return None
    times = [b.t for b in beats]
    i = bisect.bisect_right(times, t) - 1
    i = max(0, min(i, len(times) - 2))
    return times[i], times[i + 1]


def _snap_seconds_to_grid(
    t: float, beats: list[Beat], subdivisions: int, allow_triplets: bool
) -> float:
    window = _local_beat_window(t, beats)
    if window is None:
        return t
    beat_start, beat_end = window
    beat_len = beat_end - beat_start
    if beat_len <= 0:
        return t

    candidates = [beat_start + beat_len * (k / subdivisions) for k in range(-1, subdivisions + 2)]
    if allow_triplets:
        candidates += [beat_start + beat_len * (k / 3) for k in range(-1, 5)]
    return min(candidates, key=lambda c: abs(c - t))


def _beat_length_at(t: float, beats: list[Beat], fallback_bpm: float) -> float:
    window = _local_beat_window(t, beats)
    if window is not None and window[1] > window[0]:
        return window[1] - window[0]
    return 60.0 / fallback_bpm


def quantize_notes(
    notes: list[Note], grid: GridIR, subdivisions: int = 16, allow_triplets: bool = True
) -> list[Note]:
    min_ticks = duration_ticks(MIN_NOTE_VALUE, PPQ)
    quantized: list[Note] = []

    for note in notes:
        onset_snapped = _snap_seconds_to_grid(note.onset, grid.beats, subdivisions, allow_triplets)
        beat_len = _beat_length_at(onset_snapped, grid.beats, grid.tempo_bpm_global)

        duration_beats = max(0.0, (note.offset - note.onset) / beat_len)
        raw_ticks_f = duration_beats * PPQ

        if raw_ticks_f < 1.0:
            if note.conf < 0.5:
                continue  # ゴースト除去
            raw_ticks_f = 1.0

        gp_parts = quantize_to_gp_durations(round(raw_ticks_f), PPQ)
        total_ticks = sum(duration_ticks(p.value, PPQ, p.dotted, p.tuplet) for p in gp_parts)
        total_ticks = max(total_ticks, min_ticks)

        offset_snapped = onset_snapped + (total_ticks / PPQ) * beat_len
        quantized.append(note.model_copy(update={"onset": onset_snapped, "offset": offset_snapped}))

    # 同一 pitch・同一オンセットの完全重複は conf の高い方を残してマージする
    dedup: dict[tuple[float, int], Note] = {}
    for note in quantized:
        key = (round(note.onset, 4), note.pitch)
        if key not in dedup or note.conf > dedup[key].conf:
            dedup[key] = note
    return sorted(dedup.values(), key=lambda n: n.onset)


@dataclass
class Stage:
    name: str = "s6_quantize"

    def is_done(self, job: Job) -> bool:
        return job.stage_output(self.name).exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        notes_ir = ir_io.load(NotesIR, job.stage_output("s4b_fuse"))
        grid = ir_io.load(GridIR, job.stage_output("s2_rhythm"))
        quantized = quantize_notes(
            notes_ir.notes, grid,
            subdivisions=cfg.rhythm.quantize_grid,
            allow_triplets=cfg.rhythm.allow_triplets,
        )
        result = NotesIR(runs=notes_ir.runs, notes=quantized)
        ir_io.save(result, job.stage_output(self.name))
        job.logger.info(self.name, "quantized", note_count=len(quantized))
