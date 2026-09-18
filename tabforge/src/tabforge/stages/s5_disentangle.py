"""S5 Part Disentanglement（設計書 §8、実装指示書 T1-6 / T3-2 / T3-3）。

Phase A: ベース確定（P1）。
Phase B: 特徴量 F1-F10 の計算（P3, T3-2, 本ファイル `compute_features`）。
Phase C-E: ルールベース分類 + HMM 平滑化は s5_disentangle.classify_lead_rhythm
（後続タスクで追加）が担う。
"""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from itertools import pairwise

from tabforge.config import DisentangleConfig, TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import Assignment, ChordsIR, GridIR, Note, NoteFeatures, NotesIR, PartsIR
from tabforge.job import Job

BASS_INSTRUMENTS = {"electric_bass", "acoustic_bass"}
BASS_PITCH_THRESHOLD = 45
ONSET_CLUSTER_WINDOW_SEC = 0.04  # ±40ms


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


# ---------------------------------------------------------------------------
# Phase B: 特徴量 F1-F10（設計書 §8.2、実装指示書 T3-2）
# ---------------------------------------------------------------------------


def _cluster_by_onset(notes: list[Note], window: float = ONSET_CLUSTER_WINDOW_SEC) -> list[list[Note]]:
    """±window 以内のオンセットを同一クラスタとみなす（notes は onset 昇順を仮定）。"""
    clusters: list[list[Note]] = []
    for note in notes:
        if clusters and note.onset - clusters[-1][0].onset <= window:
            clusters[-1].append(note)
        else:
            clusters.append([note])
    return clusters


def _chord_tone_score(pitch_class: int, pitch_classes: list[int]) -> float:
    if not pitch_classes:
        return 0.5  # 無和音区間は中立値
    if pitch_class in pitch_classes:
        return 1.0
    min_dist = min(min((pitch_class - pc) % 12, (pc - pitch_class) % 12) for pc in pitch_classes)
    return max(0.0, 1.0 - min_dist / 6.0)


def _chord_at(t: float, chords: ChordsIR) -> list[int]:
    for seg in chords.segments:
        if seg.start <= t < seg.end:
            return seg.pitch_classes
    return []


def _on_grid_distance(t: float, beat_times: list[float], subdivisions: int = 16) -> float:
    """最近傍 16分グリッドからの距離を拍長で正規化した値。"""
    if len(beat_times) < 2:
        return 0.0
    i = bisect.bisect_right(beat_times, t) - 1
    i = max(0, min(i, len(beat_times) - 2))
    beat_start, beat_end = beat_times[i], beat_times[i + 1]
    beat_len = beat_end - beat_start
    if beat_len <= 0:
        return 0.0
    candidates = [beat_start + beat_len * (k / subdivisions) for k in range(subdivisions + 1)]
    nearest = min(candidates, key=lambda c: abs(c - t))
    return min(1.0, abs(nearest - t) / beat_len)


def _periodicity(note: Note, notes_by_bar: dict[int, set[int]], bar: int) -> float:
    """小節単位の pitch集合自己相関の簡易版:
    自分のピッチクラスが他の小節にどれだけ再出現するかの割合。"""
    other_bars = [pcs for b, pcs in notes_by_bar.items() if b != bar]
    if not other_bars:
        return 0.0
    hits = sum(1 for pcs in other_bars if (note.pitch % 12) in pcs)
    return hits / len(other_bars)


def compute_features(
    notes: list[Note], chords: ChordsIR, grid: GridIR
) -> dict[str, NoteFeatures]:
    """§8.2 の F1〜F10 を計算する。戻り値は note_id -> NoteFeatures。"""
    sorted_notes = sorted(notes, key=lambda n: n.onset)
    clusters = _cluster_by_onset(sorted_notes)
    beat_times = [b.t for b in grid.beats]
    beat_len = 60.0 / grid.tempo_bpm_global if grid.tempo_bpm_global > 0 else 0.5

    def bar_for(t: float) -> int:
        bar = 1
        for beat in grid.beats:
            if beat.t <= t:
                bar = beat.bar
            else:
                break
        return bar

    notes_by_bar: dict[int, set[int]] = {}
    for note in sorted_notes:
        notes_by_bar.setdefault(bar_for(note.onset), set()).add(note.pitch % 12)

    result: dict[str, NoteFeatures] = {}
    prev_onset: float | None = None

    for cluster in clusters:
        cluster_pitches = sorted(n.pitch for n in cluster)
        poly = len(cluster)
        cluster_width = (cluster_pitches[-1] - cluster_pitches[0]) if poly > 1 else 0

        for note in cluster:
            rank = cluster_pitches.index(note.pitch)
            register = rank / (poly - 1) if poly > 1 else 1.0

            ioi = (note.onset - prev_onset) / beat_len if prev_onset is not None else 4.0
            dur = (note.offset - note.onset) / beat_len

            pitch_classes = _chord_at(note.onset, chords)
            chord_tone = _chord_tone_score(note.pitch % 12, pitch_classes)
            on_grid = _on_grid_distance(note.onset, beat_times)
            bar = bar_for(note.onset)
            periodicity = _periodicity(note, notes_by_bar, bar)
            bend_extent = max((abs(v) for _pos, v in (note.bend_curve or [])), default=0.0)

            result[note.id] = NoteFeatures(
                poly=float(poly), chord_tone=chord_tone, on_grid=on_grid,
                register=register, ioi=ioi, pan=note.pan or 0.0, dur=dur,
                periodicity=periodicity, cluster_width=float(cluster_width),
                bend_extent=bend_extent,
            )
        prev_onset = cluster[0].onset

    return result


# ---------------------------------------------------------------------------
# Phase C: ノート単位スコアリング + オンセットクラスタ単位の集約
# ---------------------------------------------------------------------------

FORCED_RHYTHM_POLY = 3
FORCED_RHYTHM_SCORE = -10.0


def s_lead(f: NoteFeatures, weights: list[float]) -> float:
    """設計書 §8.3 Phase B の線形スコア。既定重み [1.2,0.8,0.9,1.0,1.1,0.4,0.7,0.6,1.0]。

    §8.3 の `w2·[chord_tone==0]` は chord_tone を 0/1 二値と仮定しているが、
    本実装の chord_tone は連続値 [0,1] のため `(1 - chord_tone)`（非和声音度）
    で近似する。
    """
    w1, w2, w3, w4, w5, w6, w7, w8, w9 = weights
    return (
        w1 * (1.0 if (f.poly or 0) <= 2 else 0.0)
        + w2 * (1.0 - (f.chord_tone or 0.0))
        + w3 * min((f.on_grid or 0.0) / 0.15, 1.0)
        + w4 * (f.register or 0.0)
        + w5 * (1.0 if (f.ioi or 0.0) < 0.35 else 0.0)
        + w6 * (1.0 - abs(f.pan or 0.0))
        + w7 * (1.0 - (f.periodicity or 0.0))
        + w8 * min((f.bend_extent or 0.0) / 1.0, 1.0)
        - w9 * (1.0 if (f.cluster_width or 0.0) >= 5 else 0.0)
    )


def cluster_scores(
    clusters: list[list[Note]], features: dict[str, NoteFeatures], weights: list[float]
) -> list[float]:
    scores = []
    for cluster in clusters:
        if len(cluster) >= FORCED_RHYTHM_POLY:
            scores.append(FORCED_RHYTHM_SCORE)  # 3声以上の同時発音は強制 rhythm
            continue
        vals = [s_lead(features[n.id], weights) for n in cluster]
        scores.append(sum(vals) / len(vals))
    return scores


# ---------------------------------------------------------------------------
# Phase D: 2状態 HMM の Viterbi による平滑化（★必須）
# ---------------------------------------------------------------------------


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def hmm_smooth_lead_rhythm(scores: list[float], stay_prob: float) -> list[str]:
    """観測 = クラスタスコア。状態 = {lead, rhythm}。P(stay)=hmm_stay_prob。"""
    if not scores:
        return []
    states = ("lead", "rhythm")
    trans = {
        ("lead", "lead"): stay_prob, ("lead", "rhythm"): 1 - stay_prob,
        ("rhythm", "rhythm"): stay_prob, ("rhythm", "lead"): 1 - stay_prob,
    }

    def emission(score: float, state: str) -> float:
        p_lead = _sigmoid(score)
        return p_lead if state == "lead" else 1.0 - p_lead

    log_prob = {s: math.log(max(emission(scores[0], s), 1e-9)) for s in states}
    backptrs: list[dict[str, str]] = []

    for score in scores[1:]:
        new_log_prob: dict[str, float] = {}
        step_back: dict[str, str] = {}
        for cur in states:
            best_prev, best_val = None, -math.inf
            for prev in states:
                val = log_prob[prev] + math.log(trans[(prev, cur)])
                if val > best_val:
                    best_val, best_prev = val, prev
            step_back[cur] = best_prev  # type: ignore[assignment]
            new_log_prob[cur] = best_val + math.log(max(emission(score, cur), 1e-9))
        log_prob = new_log_prob
        backptrs.append(step_back)

    last_state = max(states, key=lambda s: log_prob[s])
    path = [last_state]
    for step_back in reversed(backptrs):
        last_state = step_back[last_state]
        path.append(last_state)
    path.reverse()
    return path


def count_part_switches(states: list[str]) -> int:
    return sum(1 for a, b in pairwise(states) if a != b)


# ---------------------------------------------------------------------------
# Phase E: 区間後処理
# ---------------------------------------------------------------------------


def postprocess_regions(states: list[str], clusters: list[list[Note]], beat_len: float) -> list[str]:
    states = list(states)
    n = len(states)

    # 3声以上が lead 判定された場合の安全網（Phase C で既に score を強制しているが念のため）
    for i, cluster in enumerate(clusters):
        if len(cluster) >= FORCED_RHYTHM_POLY and states[i] == "lead":
            states[i] = "rhythm"

    # lead 区間が1拍未満で孤立 → rhythm に吸収
    i = 0
    while i < n:
        j = i
        while j < n and states[j] == states[i]:
            j += 1
        if states[i] == "lead":
            start_t = clusters[i][0].onset
            end_t = clusters[j][0].onset if j < n else clusters[j - 1][0].onset + beat_len
            if beat_len > 0 and (end_t - start_t) / beat_len < 1.0:
                for k in range(i, j):
                    states[k] = "rhythm"
        i = j

    # rhythm 区間内に単音が散発 → unassigned として保留（人手レビュー対象）
    for i, cluster in enumerate(clusters):
        if states[i] != "rhythm" or len(cluster) != 1:
            continue
        prev_state = states[i - 1] if i > 0 else None
        next_state = states[i + 1] if i < n - 1 else None
        if prev_state == "rhythm" and next_state == "rhythm":
            states[i] = "unassigned"

    return states


def classify_lead_rhythm(
    notes: list[Note], chords: ChordsIR, grid: GridIR, cfg: DisentangleConfig
) -> list[Assignment]:
    """Phase B〜E: lead/rhythm/unassigned のノート単位割当を返す（ベース以外が対象）。"""
    if not notes:
        return []

    sorted_notes = sorted(notes, key=lambda n: n.onset)
    features = compute_features(sorted_notes, chords, grid)
    clusters = _cluster_by_onset(sorted_notes)

    scores = cluster_scores(clusters, features, cfg.weights)
    raw_states = hmm_smooth_lead_rhythm(scores, cfg.hmm_stay_prob)

    beat_len = 60.0 / grid.tempo_bpm_global if grid.tempo_bpm_global > 0 else 0.5
    final_states = postprocess_regions(raw_states, clusters, beat_len)

    assignments: list[Assignment] = []
    for cluster, state in zip(clusters, final_states, strict=True):
        for note in cluster:
            f = features[note.id]
            score = _sigmoid(s_lead(f, cfg.weights)) if state != "unassigned" else 0.3
            assignments.append(Assignment(note_id=note.id, part=state, score=score, features=f))
    return assignments


@dataclass
class Stage:
    name: str = "s5_disentangle"

    def is_done(self, job: Job) -> bool:
        return job.stage_output(self.name).exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        notes_ir = ir_io.load(NotesIR, job.stage_output("s4b_fuse"))

        bass_notes = [
            n for n in notes_ir.notes
            if n.instrument in BASS_INSTRUMENTS or n.pitch < BASS_PITCH_THRESHOLD
        ]
        bass_ids = {n.id for n in bass_notes}
        guitar_notes = [n for n in notes_ir.notes if n.id not in bass_ids]

        assignments: list[Assignment] = [
            Assignment(
                note_id=n.id, part="bass",
                score=1.0 if n.instrument in BASS_INSTRUMENTS else 0.6,
            )
            for n in bass_notes
        ]

        chords_path = job.stage_output("s3_chords")
        grid_path = job.stage_output("s2_rhythm")
        if guitar_notes and cfg.disentangle.mode == "rules" and grid_path.exists():
            from tabforge.ir.models import ChordsIR as _ChordsIR

            chords = ir_io.load(_ChordsIR, chords_path) if chords_path.exists() else _ChordsIR(source="none")
            grid = ir_io.load(GridIR, grid_path)
            assignments.extend(classify_lead_rhythm(guitar_notes, chords, grid, cfg.disentangle))
        else:
            assignments.extend(
                Assignment(note_id=n.id, part="unassigned", score=0.3) for n in guitar_notes
            )

        stats = {"lead": 0, "rhythm": 0, "bass": 0, "unassigned": 0}
        for a in assignments:
            stats[a.part] += 1

        total = len(assignments)
        if total and stats["unassigned"] / total > 0.05:
            job.logger.warning(
                self.name, f"unassigned が {stats['unassigned']}/{total} 件 (5%超)。report で要確認。"
            )

        parts = PartsIR(assignments=assignments, part_stats=stats)
        ir_io.save(parts, job.stage_output(self.name))
        job.logger.info(self.name, "classified", **stats)
