"""S7 Tablature Arrangement — ベースのフレット割当のみ（実装指示書 T1-8, T2-1）。

P1 スコープ: parts.json で part="bass" と判定されたノートのみを対象に、
チューニング推定 (theory.tuning) → Viterbi フレット割当 (arrange.fretting) を
行い、単一 "Bass" トラックの tab.json を生成する。
ギター (lead/rhythm) のアレンジは P2/P3 で追加する。
"""
from __future__ import annotations

from dataclasses import dataclass

from tabforge.arrange.fretting import FretConfig, OnsetGroup, assign_frets
from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import (
    GpDuration,
    GridIR,
    Note,
    NotesIR,
    PartsIR,
    TabBeat,
    TabIR,
    TabMeasure,
    TabNote,
    TabTrack,
)
from tabforge.job import Job
from tabforge.stages.s6_quantize import PPQ
from tabforge.theory.duration import quantize_to_gp_durations
from tabforge.theory.tuning import detect_5string_bass, estimate_tuning

BASS_STANDARD = (43, 38, 33, 28)  # G2 D2 A1 E1 (index0 = 最高音弦)
BASS_5STRING = (43, 38, 33, 28, 23)  # + B0


def _bass_notes(notes_ir: NotesIR, parts: PartsIR) -> list[Note]:
    bass_ids = {a.note_id for a in parts.assignments if a.part == "bass"}
    notes = [n for n in notes_ir.notes if n.id in bass_ids]
    return sorted(notes, key=lambda n: n.onset)


def _bar_for_time(t: float, grid: GridIR) -> int:
    if not grid.beats:
        return 1
    bar = 1
    for beat in grid.beats:
        if beat.t <= t:
            bar = beat.bar
        else:
            break
    return bar


def build_bass_track(
    notes: list[Note], grid: GridIR, cfg: TabForgeConfig
) -> tuple[TabTrack, int, int]:
    pitches = [n.pitch for n in notes]
    tuning_base = BASS_5STRING if detect_5string_bass(pitches) else BASS_STANDARD
    estimate = estimate_tuning(pitches, tuning_base, kind="bass") if pitches else None
    tuning = estimate.tuning if estimate else tuning_base

    fret_cfg = FretConfig(tuning=tuning, max_fret=cfg.arrange.bass.max_fret, span_max=4)

    groups: list[OnsetGroup] = []
    for i, note in enumerate(notes):
        dt_beats = 0.0
        if i > 0:
            beat_len = 60.0 / grid.tempo_bpm_global
            dt_beats = (note.onset - notes[i - 1].onset) / beat_len if beat_len > 0 else 0.0
        groups.append(OnsetGroup(pitches=[note.pitch], dt_beats=dt_beats))

    assignments = assign_frets(groups, fret_cfg)
    in_range = [(n, g) for n, g in zip(notes, groups) if g.warning is None]
    position_jumps_gt5 = 0
    prev_fret: int | None = None

    bars: dict[int, list[TabBeat]] = {}
    for (note, _group), assign in zip(in_range, assignments):
        string_idx, fret = assign[0]
        if prev_fret is not None and abs(fret - prev_fret) > 5:
            position_jumps_gt5 += 1
        prev_fret = fret

        beat_len = 60.0 / grid.tempo_bpm_global
        duration_ticks_val = round(((note.offset - note.onset) / beat_len) * PPQ) if beat_len > 0 else PPQ
        gp_parts = quantize_to_gp_durations(max(duration_ticks_val, 1), PPQ)
        duration = gp_parts[0] if gp_parts else GpDuration(value=4)

        bar = _bar_for_time(note.onset, grid)
        tab_beat = TabBeat(
            start_tick=0,
            duration=duration,
            notes=[TabNote(string=string_idx + 1, fret=fret)],
        )
        bars.setdefault(bar, []).append(tab_beat)

    max_bar = max(bars.keys(), default=1)
    measures = [
        TabMeasure(bar=b, time_signature=(4, 4), tempo=grid.tempo_bpm_global, beats=bars.get(b, []))
        for b in range(1, max_bar + 1)
    ]

    dropped = len(notes) - len(in_range)
    track = TabTrack(
        name="Bass", part="bass", tuning=list(tuning), string_count=len(tuning), measures=measures,
    )
    return track, dropped, position_jumps_gt5


@dataclass
class Stage:
    name: str = "s7_arrange"

    def is_done(self, job: Job) -> bool:
        return job.stage_output(self.name).exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        notes_ir = ir_io.load(NotesIR, job.stage_output("s6_quantize"))
        parts = ir_io.load(PartsIR, job.stage_output("s5_disentangle"))
        grid = ir_io.load(GridIR, job.stage_output("s2_rhythm"))

        bass_notes = _bass_notes(notes_ir, parts)
        track, dropped, jumps = build_bass_track(bass_notes, grid, cfg)

        tab = TabIR(tracks=[track])
        tab.quality.note_count = sum(len(m.beats) for m in track.measures)
        tab.quality.unplayable_dropped = dropped
        tab.quality.position_jumps_gt5 = jumps

        ir_io.save(tab, job.stage_output(self.name))
        job.logger.info(
            self.name, "arranged",
            note_count=tab.quality.note_count, dropped=dropped, position_jumps_gt5=jumps,
        )
