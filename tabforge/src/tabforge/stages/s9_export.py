"""S9 Export（設計書 §10、実装指示書 T1-9）。

P1 スコープ: GP5 のみ実装する。MusicXML/MIDI/ASCII/check_mix は P4 以降で追加する。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from tabforge.config import TabForgeConfig
from tabforge.export.gp5_writer import write_gp5
from tabforge.ir import io as ir_io
from tabforge.ir.models import TabIR
from tabforge.job import Job


@dataclass
class Stage:
    name: str = "s9_export"
    formats: list[str] = field(default_factory=lambda: ["gp5"])

    def is_done(self, job: Job) -> bool:
        return (job.out_path("score.gp5")).exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        tab = ir_io.load(TabIR, job.stage_output("s7_arrange"))

        if "gp5" in self.formats:
            write_gp5(tab, job.out_path("score.gp5"), tempo=int(tab.tracks[0].measures[0].tempo)
                      if tab.tracks and tab.tracks[0].measures else 120)
            job.logger.info(self.name, "exported gp5", path=str(job.out_path("score.gp5")))

        unsupported = [f for f in self.formats if f != "gp5"]
        if unsupported:
            job.logger.warning(self.name, f"未実装フォーマット(P4以降): {unsupported}")

        # is_done の判定に使う空マーカー（score.gp5 が主成果物のため、実体はそちら）。
        marker = job.stage_output(self.name)
        marker.parent.mkdir(parents=True, exist_ok=True)
        ir_io.save(tab, marker)
