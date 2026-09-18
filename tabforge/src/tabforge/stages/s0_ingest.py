"""S0 Ingest（設計書 §6.1、実装指示書 T1-1）。

入力音源を 44.1kHz/2ch wav に統一し、LUFS 正規化・無音トリムを行う。
MuScriptor はモノラル前提のため `mix_mono.wav` も生成する。
"""
from __future__ import annotations

from dataclasses import dataclass

from tabforge.config import TabForgeConfig
from tabforge.job import Job
from tabforge.utils import audio as audio_utils


@dataclass
class Stage:
    name: str = "s0_ingest"

    def is_done(self, job: Job) -> bool:
        return (job.audio_dir / "mix.wav").exists() and (job.audio_dir / "mix_mono.wav").exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        if job.source_audio is None:
            raise ValueError("s0_ingest には source_audio が必要")

        mix_raw = job.audio_dir / "_mix_raw.wav"
        audio_utils.to_wav_stereo(job.source_audio, mix_raw)

        mix_normalized = job.audio_dir / "_mix_normalized.wav"
        audio_utils.normalize_lufs(mix_raw, mix_normalized, cfg.ingest.target_lufs)

        mix_path = job.audio_dir / "mix.wav"
        audio_utils.trim_silence(mix_normalized, mix_path)

        mono_path = job.audio_dir / "mix_mono.wav"
        audio_utils.to_mono(mix_path, mono_path)

        mix_raw.unlink(missing_ok=True)
        mix_normalized.unlink(missing_ok=True)

        job.logger.info(self.name, "ingested", mix=str(mix_path), mono=str(mono_path))
