"""S7 Tablature Arrangement（実装指示書 T1-8, T2-1, T2-4）。

チューニング推定 (theory.tuning) → Viterbi フレット割当 (arrange.fretting) を
`build_track()` に汎用化し、ベース・ギター単一トラック双方で再利用する
（T1-8: 「ベースと同じコードでギターにも使える汎用実装」）。

- Bass トラック: parts.json で part="bass" のノートから常に生成する。
- Guitar トラック: `--guitar-tracks 1` のときのみ、bass 以外の全ノートを
  1トラックにまとめて生成する（T2-4）。`guitar_tracks >= 2` のリード/
  バッキング分離は P3 (S5 Phase B-E) 実装後に別途対応する。
"""
from __future__ import annotations

from dataclasses import dataclass

from tabforge.arrange.fretting import FretConfig, OnsetGroup, assign_frets
from tabforge.arrange.voicing import Shape, StrumBeat, generate_strumming, select_voicing
from tabforge.config import TabForgeConfig, TechniqueConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import (
    ChordsIR,
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
from tabforge.stages.s8_technique import (
    build_note_effects,
    confirm_hammer_or_slide,
    is_legato_candidate,
)
from tabforge.theory.duration import quantize_to_gp_durations
from tabforge.theory.tuning import detect_5string_bass, estimate_tuning

BASS_STANDARD = (43, 38, 33, 28)  # G2 D2 A1 E1 (index0 = 最高音弦)
BASS_5STRING = (43, 38, 33, 28, 23)  # + B0
GUITAR_STANDARD = (64, 59, 55, 50, 45, 40)  # E4 B3 G3 D3 A2 E2


def _notes_for_part(notes_ir: NotesIR, parts: PartsIR, part_names: set[str]) -> list[Note]:
    ids = {a.note_id for a in parts.assignments if a.part in part_names}
    notes = [n for n in notes_ir.notes if n.id in ids]
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


def _group_notes_by_onset(notes: list[Note]) -> list[list[Note]]:
    """同一 tick（S6 で吸着済み）のノートを和音グループにまとめる。"""
    groups: dict[float, list[Note]] = {}
    for note in notes:
        groups.setdefault(round(note.onset, 4), []).append(note)
    return [groups[key] for key in sorted(groups)]


def _total_bars(grid: GridIR) -> int:
    return max((b.bar for b in grid.beats), default=1)


def build_track(
    notes: list[Note], grid: GridIR, tuning: tuple[int, ...], max_fret: int,
    name: str, part: str, total_bars: int | None = None,
    technique_cfg: TechniqueConfig | None = None,
) -> tuple[TabTrack, int, int]:
    """フレット割当の汎用実装（T1-8: ベースと同じコードでギターにも使える）。

    `technique_cfg` を渡すと S8 技法推定（T4-1/T4-2）を統合する。HO/PO・
    スライド候補は Viterbi 実行前に `OnsetGroup.legato_links` として渡し
    同一弦維持を強制、確定後の実フレット差で最終判定する二段階方式。
    """
    note_groups = _group_notes_by_onset(notes)
    fret_cfg = FretConfig(tuning=tuning, max_fret=max_fret, span_max=4)

    beat_len = 60.0 / grid.tempo_bpm_global if grid.tempo_bpm_global > 0 else 0.5
    onset_groups: list[OnsetGroup] = []
    for i, group in enumerate(note_groups):
        dt_beats = 0.0
        legato = False
        if i > 0:
            dt_beats = (group[0].onset - note_groups[i - 1][0].onset) / beat_len
            if technique_cfg is not None and len(group) == 1 and len(note_groups[i - 1]) == 1:
                legato = is_legato_candidate(note_groups[i - 1][0], group[0], dt_beats)
        onset_groups.append(
            OnsetGroup(pitches=[n.pitch for n in group], dt_beats=dt_beats,
                       legato_links={0} if legato else set())
        )

    assignments = assign_frets(onset_groups, fret_cfg)
    in_range = [(g, og) for g, og in zip(note_groups, onset_groups) if og.warning is None]

    position_jumps_gt5 = 0
    prev_center: float | None = None
    prev_assign: tuple[tuple[int, int], ...] | None = None
    bars: dict[int, list[TabBeat]] = {}

    for idx, ((group, _og), assign) in enumerate(zip(in_range, assignments)):
        center = sum(fret for _si, fret in assign) / len(assign)
        if prev_center is not None and abs(center - prev_center) > 5:
            position_jumps_gt5 += 1

        rep_note = group[0]
        duration_ticks_val = round(((rep_note.offset - rep_note.onset) / beat_len) * PPQ)
        gp_parts = quantize_to_gp_durations(max(duration_ticks_val, 1), PPQ)
        duration = gp_parts[0] if gp_parts else GpDuration(value=4)

        tab_notes: list[TabNote] = []
        if technique_cfg is not None and len(group) == 1 and len(assign) == 1:
            hammer, slide = False, None
            if prev_assign is not None and len(prev_assign) == 1:
                dt = (rep_note.onset - in_range[idx - 1][0][0].onset) / beat_len if idx > 0 else 0.0
                same_string = assign[0][0] == prev_assign[0][0]
                fret_diff = assign[0][1] - prev_assign[0][1]
                hammer, slide = confirm_hammer_or_slide(dt, fret_diff, same_string, technique_cfg)
            next_note = in_range[idx + 1][0][0] if idx + 1 < len(in_range) else None
            effects = build_note_effects(rep_note, next_note, hammer, slide, technique_cfg)
            tab_notes.append(TabNote(string=assign[0][0] + 1, fret=assign[0][1], effects=effects))
        else:
            tab_notes = [TabNote(string=si + 1, fret=fret) for si, fret in assign]

        bar = _bar_for_time(rep_note.onset, grid)
        tab_beat = TabBeat(start_tick=0, duration=duration, notes=tab_notes)
        bars.setdefault(bar, []).append(tab_beat)

        prev_center = center
        prev_assign = assign

    max_bar = max(total_bars or 1, max(bars.keys(), default=1))
    measures = [
        TabMeasure(bar=b, time_signature=(4, 4), tempo=grid.tempo_bpm_global, beats=bars.get(b, []))
        for b in range(1, max_bar + 1)
    ]

    dropped = len(note_groups) - len(in_range)
    track = TabTrack(name=name, part=part, tuning=list(tuning), string_count=len(tuning), measures=measures)
    return track, dropped, position_jumps_gt5


def build_bass_track(
    notes: list[Note], grid: GridIR, cfg: TabForgeConfig, total_bars: int | None = None
) -> tuple[TabTrack, int, int]:
    pitches = [n.pitch for n in notes]
    tuning_base = BASS_5STRING if detect_5string_bass(pitches) else BASS_STANDARD
    estimate = estimate_tuning(pitches, tuning_base, kind="bass") if pitches else None
    tuning = estimate.tuning if estimate else tuning_base
    return build_track(
        notes, grid, tuning, cfg.arrange.bass.max_fret, "Bass", "bass", total_bars,
        technique_cfg=cfg.technique,
    )


def build_guitar_track(
    notes: list[Note], grid: GridIR, cfg: TabForgeConfig, total_bars: int | None = None
) -> tuple[TabTrack, int, int]:
    """`--guitar-tracks 1`: lead/rhythm を分離せず全ギターノートを1トラックに出す（T2-4）。"""
    pitches = [n.pitch for n in notes]
    estimate = estimate_tuning(pitches, GUITAR_STANDARD, kind="guitar") if pitches else None
    tuning = estimate.tuning if estimate else GUITAR_STANDARD
    # part は schema 上 lead/rhythm/bass/unassigned のいずれかのみ許容されるため、
    # 単一トラック(未分離)の便宜上 "lead" とする。
    return build_track(
        notes, grid, tuning, cfg.arrange.guitar.max_fret, "Guitar", "lead", total_bars,
        technique_cfg=cfg.technique,
    )


def build_lead_track(
    notes: list[Note], grid: GridIR, cfg: TabForgeConfig, total_bars: int | None = None
) -> tuple[TabTrack, int, int]:
    pitches = [n.pitch for n in notes]
    estimate = estimate_tuning(pitches, GUITAR_STANDARD, kind="guitar") if pitches else None
    tuning = estimate.tuning if estimate else GUITAR_STANDARD
    return build_track(
        notes, grid, tuning, cfg.arrange.guitar.max_fret, "Lead Guitar", "lead", total_bars,
        technique_cfg=cfg.technique,
    )


def build_rhythm_track(
    rhythm_notes: list[Note], chords: ChordsIR, grid: GridIR, total_bars: int | None = None,
    tuning: tuple[int, ...] = GUITAR_STANDARD,
) -> tuple[TabTrack, int]:
    """T3-4: LVCR のコードネーム＋実発音からボイシング選択・ストローク生成する。"""
    bars: dict[int, list[TabBeat]] = {}
    dropped = 0
    prev_shape: Shape | None = None

    for seg in chords.segments:
        seg_notes = [n for n in rhythm_notes if seg.start <= n.onset < seg.end]
        shape = select_voicing(seg, seg_notes, prev_shape, tuning)
        if shape is None:
            dropped += 1
            continue
        prev_shape = shape

        strokes = generate_strumming(seg_notes, grid, subdivisions=2)
        if not strokes:
            strokes = [StrumBeat(time=seg.start, stroke="down")]

        tab_notes = [TabNote(string=i + 1, fret=f) for i, f in enumerate(shape.frets) if f is not None]
        for strum in strokes:
            bar = _bar_for_time(strum.time, grid)
            tab_beat = TabBeat(
                start_tick=0, duration=GpDuration(value=8), stroke=strum.stroke,
                chord=seg.label, notes=list(tab_notes),
            )
            bars.setdefault(bar, []).append(tab_beat)

    max_bar = max(total_bars or 1, max(bars.keys(), default=1))
    measures = [
        TabMeasure(bar=b, time_signature=(4, 4), tempo=grid.tempo_bpm_global, beats=bars.get(b, []))
        for b in range(1, max_bar + 1)
    ]
    track = TabTrack(
        name="Rhythm Guitar", part="rhythm", tuning=list(tuning), string_count=len(tuning), measures=measures,
    )
    return track, dropped


@dataclass
class Stage:
    name: str = "s7_arrange"

    def is_done(self, job: Job) -> bool:
        return job.stage_output(self.name).exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        notes_ir = ir_io.load(NotesIR, job.stage_output("s6_quantize"))
        parts = ir_io.load(PartsIR, job.stage_output("s5_disentangle"))
        grid = ir_io.load(GridIR, job.stage_output("s2_rhythm"))

        tracks = []
        total_dropped = 0
        total_jumps = 0
        total_bars = _total_bars(grid)

        bass_notes = _notes_for_part(notes_ir, parts, {"bass"})
        bass_track, dropped, jumps = build_bass_track(bass_notes, grid, cfg, total_bars)
        tracks.append(bass_track)
        total_dropped += dropped
        total_jumps += jumps

        if cfg.disentangle.guitar_tracks == 1:
            guitar_notes = _notes_for_part(notes_ir, parts, {"lead", "rhythm", "unassigned"})
            if guitar_notes:
                guitar_track, g_dropped, g_jumps = build_guitar_track(guitar_notes, grid, cfg, total_bars)
                tracks.append(guitar_track)
                total_dropped += g_dropped
                total_jumps += g_jumps
        elif cfg.disentangle.guitar_tracks >= 2:
            if cfg.disentangle.guitar_tracks >= 3:
                job.logger.warning(
                    self.name,
                    "guitar_tracks>=3 の複数リード分割(K-means, T3-5)は未実装。"
                    " Lead Guitar 1本 + Rhythm Guitar として出力する。",
                )

            lead_notes = _notes_for_part(notes_ir, parts, {"lead"})
            if lead_notes:
                lead_track, l_dropped, l_jumps = build_lead_track(lead_notes, grid, cfg, total_bars)
                tracks.append(lead_track)
                total_dropped += l_dropped
                total_jumps += l_jumps

            rhythm_notes = _notes_for_part(notes_ir, parts, {"rhythm", "unassigned"})
            chords_path = job.stage_output("s3_chords")
            chords = ir_io.load(ChordsIR, chords_path) if chords_path.exists() else ChordsIR(source="none")
            if chords.segments:
                rhythm_track, r_dropped = build_rhythm_track(rhythm_notes, chords, grid, total_bars)
                tracks.append(rhythm_track)
                total_dropped += r_dropped
            elif rhythm_notes:
                job.logger.warning(
                    self.name,
                    "chords.json が空のため Rhythm Guitar のボイシング選択をスキップした"
                    "（chords.recognizer=manual で chords_manual.json を用意すること）。",
                )

        tab = TabIR(tracks=tracks)
        tab.quality.note_count = sum(len(m.beats) for t in tracks for m in t.measures)
        tab.quality.unplayable_dropped = total_dropped
        tab.quality.position_jumps_gt5 = total_jumps

        ir_io.save(tab, job.stage_output(self.name))
        job.logger.info(
            self.name, "arranged",
            note_count=tab.quality.note_count, dropped=total_dropped, position_jumps_gt5=total_jumps,
        )
