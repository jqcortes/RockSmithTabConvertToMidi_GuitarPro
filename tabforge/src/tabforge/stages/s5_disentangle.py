"""S5 Part Disentanglement — Phase A のみ（設計書 §8.3、実装指示書 T1-6）。

P1 スコープではベース確定のみ実装する。ギターの lead/rhythm 分類
（Phase B〜E, HMM 平滑化）は P3 (T3-3) で追加する。
"""
from __future__ import annotations

from dataclasses import dataclass

from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import Assignment, NotesIR, PartsIR
from tabforge.job import Job

BASS_INSTRUMENTS = {"electric_bass", "acoustic_bass"}
BASS_PITCH_THRESHOLD = 45


def classify_phase_a(notes_ir: NotesIR) -> PartsIR:
    assignments: list[Assignment] = []
    stats = {"lead": 0, "rhythm": 0, "bass": 0, "unassigned": 0}
    for note in notes_ir.notes:
        if note.instrument in BASS_INSTRUMENTS:
            part, score = "bass", 1.0
        elif note.pitch < BASS_PITCH_THRESHOLD:
            # ベースステムのエネルギー支配判定は要音声解析のため P1 では省略し、
            # ピッチのみで暫定判定する（conf を下げて report で分かるようにする）。
            part, score = "bass", 0.6
        else:
            part, score = "unassigned", 0.3
        assignments.append(Assignment(note_id=note.id, part=part, score=score))
        stats[part] += 1
    return PartsIR(assignments=assignments, part_stats=stats)


@dataclass
class Stage:
    name: str = "s5_disentangle"

    def is_done(self, job: Job) -> bool:
        return job.stage_output(self.name).exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        notes_ir = ir_io.load(NotesIR, job.stage_output("s4b_fuse"))
        parts = classify_phase_a(notes_ir)
        ir_io.save(parts, job.stage_output(self.name))
        job.logger.info(self.name, "classified", **parts.part_stats)
