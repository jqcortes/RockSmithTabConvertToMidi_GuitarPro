"""Job / JobDir とステージキャッシュ管理。

各ステージは `ir/<name>.json` の存在有無でキャッシュ判定する（D5: 全段の
中間表現を JSON で外部化し、段ごとにキャッシュ・再実行可能にする）。
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from tabforge.config import TabForgeConfig
from tabforge.utils.logging import StageLogger

# パイプラインの実行順序。--from/--to の解決に使う。
STAGE_ORDER = [
    "s0_ingest",
    "s1_separate",
    "s2_rhythm",
    "s3_chords",
    "s4_transcribe",
    "s4b_fuse",
    "s5_disentangle",
    "s6_quantize",
    "s7_arrange",
    "s9_export",
]


class Stage(Protocol):
    name: str

    def is_done(self, job: Job) -> bool: ...

    def run(self, job: Job, cfg: TabForgeConfig) -> None: ...


def job_id_from_audio(audio_path: Path) -> str:
    digest = hashlib.sha1(audio_path.read_bytes()).hexdigest()
    return digest[:12]


@dataclass
class Job:
    job_dir: Path
    source_audio: Path | None = None
    logger: StageLogger = field(default_factory=StageLogger)

    def __post_init__(self) -> None:
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.ir_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    @property
    def ir_dir(self) -> Path:
        return self.job_dir / "ir"

    @property
    def audio_dir(self) -> Path:
        return self.job_dir / "audio"

    @property
    def stems_dir(self) -> Path:
        return self.audio_dir / "stems"

    def stage_output(self, name: str) -> Path:
        """IR ステージの標準出力パス（ir/<name>.json）。"""
        return self.ir_dir / f"{name}.json"

    def out_path(self, filename: str) -> Path:
        return self.job_dir / filename

    def is_cached(self, name: str) -> bool:
        return self.stage_output(name).exists()

    def run_stage(self, stage: Stage, cfg: TabForgeConfig, force: bool = False) -> None:
        if stage.is_done(self) and not force:
            self.logger.info(stage.name, "cached", duration_sec=0.0)
            return
        started = time.monotonic()
        try:
            stage.run(self, cfg)
        except Exception as exc:
            self.logger.error(stage.name, str(exc))
            raise
        else:
            self.logger.info(stage.name, "done", duration_sec=time.monotonic() - started)

    def run_pipeline(
        self,
        stages: list[Stage],
        cfg: TabForgeConfig,
        from_stage: str | None = None,
        to_stage: str | None = None,
        force_stages: set[str] | None = None,
    ) -> None:
        force_stages = force_stages or set()
        names = [s.name for s in stages]
        start_idx = names.index(from_stage) if from_stage else 0
        end_idx = names.index(to_stage) if to_stage else len(names) - 1
        for stage in stages[start_idx : end_idx + 1]:
            self.run_stage(stage, cfg, force=stage.name in force_stages)
