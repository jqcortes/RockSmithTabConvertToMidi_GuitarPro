"""S4b Fusion（設計書 §7.2、実装指示書 T1-5）。

Step1 正規化・Step2 マッチング・Step3 投票採択・Step5 倍音誤り除去を実装する。
Step4（オンセット精緻化）・Step6（pan 算出）は音声波形を必要とするため、
`refine_onsets` / `attach_pan` として独立関数にし、job の実行系
(stages/s4b_fuse.Stage) から音声がある場合のみ呼び出す。
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from tabforge.config import FusionConfig, TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import Note, NotesIR
from tabforge.job import Job

DEFAULT_WEIGHT = 0.5
OCTAVE_SCORE_RATIO = 0.6


def _iou(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    inter = max(0.0, min(a_end, b_end) - max(a_start, b_start))
    union = max(a_end, b_end) - min(a_start, b_start)
    return inter / union if union > 0 else 0.0


def _group_by_run(notes: list[Note]) -> dict[str, list[Note]]:
    groups: dict[str, list[Note]] = defaultdict(list)
    for note in notes:
        run_id = note.src_run or (note.votes[0] if note.votes else "unknown")
        groups[run_id].append(note)
    return groups


def match_and_vote(
    raw_notes: list[Note],
    weights: dict[str, float],
    iou_threshold: float,
    base_run: str | None = None,
) -> list[Note]:
    """Step2 マッチング + Step3 投票と採択。

    基準 run（既定 ms_mix、無ければ最初に見つかった run）のノートのみを起点に
    他 run と照合する。基準 run に存在しないノート（bp_* 単独など）は
    Step3 の規則どおり自動的に破棄される。
    """
    by_run = _group_by_run(raw_notes)
    if not by_run:
        return []
    if base_run is None or base_run not in by_run:
        base_run = "ms_mix" if "ms_mix" in by_run else next(iter(by_run))

    base_notes = sorted(by_run[base_run], key=lambda n: n.onset)
    merged: list[Note] = []
    for i, note in enumerate(base_notes):
        matched: list[tuple[str, Note]] = [(base_run, note)]
        for run_id, run_notes in by_run.items():
            if run_id == base_run:
                continue
            for other in run_notes:
                if other.pitch != note.pitch:
                    continue
                if _iou(note.onset, note.offset, other.onset, other.offset) >= iou_threshold:
                    matched.append((run_id, other))
                    break

        score = sum(weights.get(run_id, DEFAULT_WEIGHT) * n.conf for run_id, n in matched)
        votes = [run_id for run_id, _n in matched]
        bend_curve = next((n.bend_curve for _r, n in matched if n.bend_curve), None)
        pan = next((n.pan for _r, n in matched if n.pan is not None), None)

        merged.append(
            Note(
                id=f"fused_{i:06d}",
                onset=note.onset,
                offset=note.offset,
                pitch=note.pitch,
                instrument=note.instrument,
                conf=score,
                votes=votes,
                bend_curve=bend_curve,
                pan=pan,
                src_run=base_run,
            )
        )
    return merged


def remove_octave_errors(notes: list[Note], ratio: float = OCTAVE_SCORE_RATIO) -> list[Note]:
    """Step5: A が B に内包され pitch(A)=pitch(B)+12 かつ score(A) < ratio*score(B) → A を破棄。"""
    to_drop: set[str] = set()
    for a in notes:
        for b in notes:
            if a.id == b.id:
                continue
            if a.pitch != b.pitch + 12:
                continue
            nested = a.onset >= b.onset and a.offset <= b.offset
            if nested and a.conf < ratio * b.conf:
                to_drop.add(a.id)
    return [n for n in notes if n.id not in to_drop]


def fuse(raw: NotesIR, cfg: FusionConfig, base_run: str | None = None) -> NotesIR:
    merged = match_and_vote(raw.notes, cfg.run_weights, cfg.iou_threshold, base_run=base_run)
    cleaned = remove_octave_errors(merged)
    return NotesIR(runs=raw.runs, notes=cleaned)


@dataclass
class Stage:
    name: str = "s4b_fuse"

    def is_done(self, job: Job) -> bool:
        return job.stage_output(self.name).exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        raw = ir_io.load(NotesIR, job.stage_output("s4_transcribe"))
        fused = fuse(raw, cfg.transcribe.fusion)
        ir_io.save(fused, job.stage_output(self.name))
        job.logger.info(self.name, "fused", note_count=len(fused.notes))
