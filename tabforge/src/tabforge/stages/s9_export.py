"""S9 Export（設計書 §10、実装指示書 T1-9 / T4-3）。

実装済み: gp5 / musicxml / ascii / midi / check_mix（簡易サイン波合成、fluidsynth 不使用）。
report.html は `formats` に関わらず常に生成する（設計書 §1.2 の成果物一覧）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from tabforge.config import TabForgeConfig
from tabforge.export.ascii_tab import write_ascii_tab
from tabforge.export.auralize import write_check_mix
from tabforge.export.gp5_writer import write_gp5
from tabforge.export.midi_writer import write_midi
from tabforge.export.musicxml_writer import write_musicxml
from tabforge.export.report import write_report
from tabforge.ir import io as ir_io
from tabforge.ir.models import GridIR, NotesIR, PartsIR, TabIR
from tabforge.job import Job

SUPPORTED_FORMATS = {"gp5", "musicxml", "ascii", "midi", "check_mix"}


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

        if "midi" in self.formats:
            write_midi(tab, job.out_path("score.mid"))
            job.logger.info(self.name, "exported midi", path=str(job.out_path("score.mid")))

        if "check_mix" in self.formats:
            mix_wav = job.audio_dir / "mix.wav"
            if mix_wav.exists():
                write_check_mix(tab, mix_wav, job.out_path("check_mix.wav"))
                job.logger.info(self.name, "exported check_mix", path=str(job.out_path("check_mix.wav")))
            else:
                job.logger.warning(self.name, "mix.wav が無いため check_mix.wav をスキップした")

        unsupported = [f for f in self.formats if f not in SUPPORTED_FORMATS]
        if unsupported:
            job.logger.warning(self.name, f"未実装フォーマット: {unsupported}")

        notes_ir = ir_io.load(NotesIR, job.stage_output("s6_quantize"))
        parts = ir_io.load(PartsIR, job.stage_output("s5_disentangle"))
        grid = ir_io.load(GridIR, job.stage_output("s2_rhythm"))
        write_report(notes_ir, parts, grid, tab, job.out_path("report.html"))
        job.logger.info(self.name, "exported report", path=str(job.out_path("report.html")))

        # is_done の判定に使う空マーカー（score.gp5 が主成果物のため、実体はそちら）。
        marker = job.stage_output(self.name)
        marker.parent.mkdir(parents=True, exist_ok=True)
        ir_io.save(tab, marker)
