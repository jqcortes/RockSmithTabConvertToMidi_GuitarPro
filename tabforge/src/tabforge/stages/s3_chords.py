"""S3 Chord Recognition（設計書 §6.3、実装指示書 T3-1）。

LVCR コンテナが落ちても degraded（無和音="N"）で全体が完走することを保証する。
"""
from __future__ import annotations

from dataclasses import dataclass

from tabforge.config import TabForgeConfig
from tabforge.engines.chord_recognizer import (
    ChordRecognizer,
    ChordRecognizerUnavailable,
    LvcrDockerRecognizer,
    MadmomRecognizer,
    ManualJsonRecognizer,
)
from tabforge.ir import io as ir_io
from tabforge.ir.models import ChordsIR, GridIR
from tabforge.job import Job
from tabforge.theory.chords import parse_chord_label

SNAP_TOLERANCE_SEC = 0.12  # ±120ms


def _build_recognizer(cfg: TabForgeConfig, job: Job) -> ChordRecognizer:
    kind = cfg.chords.recognizer
    if kind == "manual":
        return ManualJsonRecognizer(job.job_dir / "chords_manual.json")
    if kind == "madmom":
        return MadmomRecognizer()
    if kind == "lvcr_docker":
        return LvcrDockerRecognizer(job.job_dir)
    raise ValueError(f"未知の chords.recognizer: {kind!r}")


def enrich_pitch_classes(chords: ChordsIR) -> ChordsIR:
    """`pitch_classes` が未設定のセグメントをラベルから展開する。"""
    enriched = []
    for seg in chords.segments:
        if seg.pitch_classes:
            enriched.append(seg)
            continue
        info = parse_chord_label(seg.label)
        enriched.append(
            seg.model_copy(update={
                "root": info.root, "quality": info.quality, "bass": info.bass,
                "pitch_classes": list(info.pitch_classes),
            })
        )
    return ChordsIR(source=chords.source, segments=enriched)


def align_segments_to_grid(
    chords: ChordsIR, grid: GridIR, min_segment_beats: float,
    snap_tolerance_sec: float = SNAP_TOLERANCE_SEC,
) -> ChordsIR:
    """開始/終了を最近傍ビートに吸着し(±120ms)、1拍未満の区間を前後に吸収する。"""
    if not grid.beats or not chords.segments:
        return chords

    beat_times = [b.t for b in grid.beats]

    def snap(t: float) -> float:
        nearest = min(beat_times, key=lambda bt: abs(bt - t))
        return nearest if abs(nearest - t) <= snap_tolerance_sec else t

    snapped = [seg.model_copy(update={"start": snap(seg.start), "end": snap(seg.end)}) for seg in chords.segments]

    beat_len = 60.0 / grid.tempo_bpm_global if grid.tempo_bpm_global > 0 else 0.5
    min_duration = min_segment_beats * beat_len

    merged = []
    for seg in snapped:
        if merged and (seg.end - seg.start) < min_duration:
            prev = merged[-1]
            merged[-1] = prev.model_copy(update={"end": seg.end})
        else:
            merged.append(seg)

    return ChordsIR(source=chords.source, segments=merged)


@dataclass
class Stage:
    name: str = "s3_chords"

    def is_done(self, job: Job) -> bool:
        return job.stage_output(self.name).exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        recognizer = _build_recognizer(cfg, job)
        mix = job.audio_dir / "mix.wav"

        try:
            chords = recognizer.recognize(mix)
        except ChordRecognizerUnavailable as exc:
            job.logger.warning(self.name, f"degraded (no-chord): {exc}")
            chords = ChordsIR(source="none", segments=[])

        grid_path = job.stage_output("s2_rhythm")
        if grid_path.exists():
            grid = ir_io.load(GridIR, grid_path)
            chords = align_segments_to_grid(chords, grid, cfg.chords.min_segment_beats)

        chords = enrich_pitch_classes(chords)
        ir_io.save(chords, job.stage_output(self.name))
        job.logger.info(self.name, "recognized", segment_count=len(chords.segments), source=chords.source)
