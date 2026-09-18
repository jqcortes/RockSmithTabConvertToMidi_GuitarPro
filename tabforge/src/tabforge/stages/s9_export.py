"""S9 Export（設計書 §10、実装指示書 T1-9 / T4-3）。

実装済み: gp5 / musicxml / ascii。
未実装(P5以降): midi（検証用）/ check_mix（fluidsynth 合成による耳検証用ステレオ wav）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from tabforge.config import TabForgeConfig
from tabforge.export.ascii_tab import write_ascii_tab
from tabforge.export.gp5_writer import write_gp5
from tabforge.export.musicxml_writer import write_musicxml
from tabforge.ir import io as ir_io
from tabforge.ir.models import TabIR
from tabforge.job import Job

SUPPORTED_FORMATS = {"gp5", "musicxml", "ascii"}


@dataclass
class Stage:
    name: str = "s9_export"
    formats: list[str] = field(default_factory=lambda: ["gp5"])

    def is_done(self, job: Job) -> bool:
        return (job.out_path("score.gp5")).exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        tab = ir_io.load(TabIR, job.stage_output("s7_arrange"))
        tempo = int(tab.tracks[0].measures[0].tempo) if tab.tracks and tab.tracks[0].measures else 120

        if "gp5" in self.formats:
            write_gp5(tab, job.out_path("score.gp5"), tempo=tempo)
            job.logger.info(self.name, "exported gp5", path=str(job.out_path("score.gp5")))

        if "musicxml" in self.formats:
            write_musicxml(tab, job.out_path("score.musicxml"))
            job.logger.info(self.name, "exported musicxml", path=str(job.out_path("score.musicxml")))

        if "ascii" in self.formats:
            write_ascii_tab(tab, job.out_path("score.txt"))
            job.logger.info(self.name, "exported ascii", path=str(job.out_path("score.txt")))

        unsupported = [f for f in self.formats if f not in SUPPORTED_FORMATS]
        if unsupported:
            job.logger.warning(self.name, f"未実装フォーマット(P5以降): {unsupported}")

        # is_done の判定に使う空マーカー（score.gp5 が主成果物のため、実体はそちら）。
        marker = job.stage_output(self.name)
        marker.parent.mkdir(parents=True, exist_ok=True)
        ir_io.save(tab, marker)
