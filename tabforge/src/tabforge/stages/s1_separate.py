"""S1 Separate（設計書 §6.2 相当、実装指示書 T1-2）。

Demucs でステム分離する。demucs が使えない場合や `--no-separate` 指定時は
degraded モードで mix.wav をそのまま "mix" ステムとして扱う（R6: 失敗を
封じ込めて全体を完走させる）。
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass

from tabforge.config import TabForgeConfig
from tabforge.engines.separator import Separator, SeparatorUnavailable
from tabforge.job import Job


@dataclass
class Stage:
    name: str = "s1_separate"

    def is_done(self, job: Job) -> bool:
        return job.stems_dir.exists() and any(job.stems_dir.glob("*.wav"))

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        mix_wav = job.audio_dir / "mix.wav"
        job.stems_dir.mkdir(parents=True, exist_ok=True)

        if cfg.separate.model == "none":
            shutil.copy(mix_wav, job.stems_dir / "mix.wav")
            job.logger.info(self.name, "no-separate: mix のみ使用")
            return

        separator = Separator()
        try:
            stems = separator.run(
                mix_wav,
                job.job_dir / "_demucs_out",
                model=cfg.separate.model,
                shifts=cfg.separate.shifts,
                overlap=cfg.separate.overlap,
                device=cfg.separate.device,
            )
        except SeparatorUnavailable as exc:
            job.logger.warning(self.name, f"degraded: {exc}")
            shutil.copy(mix_wav, job.stems_dir / "mix.wav")
            return

        for stem_name, path in stems.items():
            shutil.copy(path, job.stems_dir / f"{stem_name}.wav")

        if "guitar" not in stems and "other" in stems:
            job.logger.warning(self.name, "4stem モデルにフォールバック: other を guitar として扱う")
            shutil.copy(job.stems_dir / "other.wav", job.stems_dir / "guitar.wav")

        job.logger.info(self.name, "separated", stems=sorted(stems.keys()))
