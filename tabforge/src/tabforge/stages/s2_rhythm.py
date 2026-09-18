"""S2 Rhythm Analysis（設計書 §6.2、実装指示書 T1-3）。

まず librosa.beat.beat_track による最小実装（+ 手動オーバーライド）とし、
学習型トラッカーへの差し替えは P6 (T6-1) で `BeatTracker` の別実装を足すだけ
で済むようにする。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from tabforge.config import ManualRhythm, TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import Beat, GridIR, TempoPoint, TimeSignature
from tabforge.job import Job

TEMPO_STABILITY_TOLERANCE = 0.03  # ±3% 以内なら単一テンポに丸める


class BeatTracker(Protocol):
    def track(self, mix_mono: Path, drums: Path | None) -> GridIR: ...


def _round_tempo_map(bpms: list[float], global_bpm: float) -> list[float]:
    """変動が ±3% 以内なら単一テンポに丸める（可読性優先）。"""
    if not bpms:
        return [global_bpm]
    lo, hi = global_bpm * (1 - TEMPO_STABILITY_TOLERANCE), global_bpm * (1 + TEMPO_STABILITY_TOLERANCE)
    if all(lo <= b <= hi for b in bpms):
        return [global_bpm]
    return bpms


class LibrosaBeatTracker:
    """フォールバック実装。drums ステムがあれば相互一致度を conf に使う。"""

    def track(self, mix_mono: Path, drums: Path | None) -> GridIR:
        import librosa

        y, sr = librosa.load(str(mix_mono), sr=None, mono=True)
        duration_sec = float(librosa.get_duration(y=y, sr=sr))

        tempo_mix, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        tempo_mix = float(np.atleast_1d(tempo_mix)[0])
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        conf = 0.75
        if drums is not None and drums.exists():
            y_d, sr_d = librosa.load(str(drums), sr=sr, mono=True)
            tempo_drums, _ = librosa.beat.beat_track(y=y_d, sr=sr_d)
            tempo_drums = float(np.atleast_1d(tempo_drums)[0])
            conf = max(0.0, 1.0 - abs(tempo_mix - tempo_drums) / max(tempo_mix, tempo_drums))

        beats: list[Beat] = []
        for i, t in enumerate(beat_times):
            beat_in_bar = (i % 4) + 1
            beats.append(
                Beat(t=t, beat_in_bar=beat_in_bar, bar=i // 4 + 1, is_downbeat=beat_in_bar == 1, conf=conf)
            )

        # tempo_map: 8拍窓の移動中央値
        window = 8
        local_bpms: list[float] = []
        for i in range(1, len(beat_times)):
            intervals = np.diff(beat_times[max(0, i - window) : i + 1])
            if intervals.size == 0:
                continue
            local_bpms.append(60.0 / float(np.median(intervals)))
        rounded = _round_tempo_map(local_bpms, tempo_mix)
        tempo_map = [TempoPoint(t=0.0, bpm=rounded[0])] if len(rounded) == 1 else [
            TempoPoint(t=beat_times[i], bpm=b) for i, b in enumerate(rounded) if i < len(beat_times)
        ]

        warnings: list[str] = []
        if conf < 0.5:
            warnings.append("テンポ検出が不安定。手動 BPM 指定を推奨")

        return GridIR(
            sample_rate=sr,
            duration_sec=duration_sec,
            tempo_bpm_global=tempo_mix,
            time_signature=TimeSignature(numerator=4, denominator=4),
            beats=beats,
            tempo_map=tempo_map,
            warnings=warnings,
        )


def _parse_time_sig(text: str) -> TimeSignature:
    num, den = text.split("/")
    return TimeSignature(numerator=int(num), denominator=int(den))


def _manual_grid(mix_mono: Path, manual: ManualRhythm) -> GridIR:
    import soundfile as sf

    info = sf.info(str(mix_mono))
    bpm = manual.bpm
    assert bpm is not None
    offset = manual.offset or 0.0
    time_sig = _parse_time_sig(manual.time_signature or "4/4")
    beat_interval = 60.0 / bpm

    beats: list[Beat] = []
    t = offset
    i = 0
    while t < info.duration:
        beat_in_bar = (i % time_sig.numerator) + 1
        beats.append(
            Beat(t=t, beat_in_bar=beat_in_bar, bar=i // time_sig.numerator + 1,
                 is_downbeat=beat_in_bar == 1, conf=1.0)
        )
        i += 1
        t = offset + i * beat_interval

    return GridIR(
        sample_rate=info.samplerate,
        duration_sec=info.duration,
        tempo_bpm_global=bpm,
        time_signature=time_sig,
        beats=beats,
        tempo_map=[TempoPoint(t=0.0, bpm=bpm)],
        warnings=[],
    )


@dataclass
class Stage:
    name: str = "s2_rhythm"

    def is_done(self, job: Job) -> bool:
        return job.stage_output(self.name).exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        mono = job.audio_dir / "mix_mono.wav"
        manual = cfg.rhythm.manual

        if manual.bpm is not None:
            grid = _manual_grid(mono, manual)
            job.logger.info(self.name, "manual override", bpm=manual.bpm)
        else:
            drums = job.stems_dir / "drums.wav"
            tracker = LibrosaBeatTracker()
            grid = tracker.track(mono, drums if drums.exists() else None)
            job.logger.info(self.name, "estimated", bpm=grid.tempo_bpm_global)

        ir_io.save(grid, job.stage_output(self.name))
