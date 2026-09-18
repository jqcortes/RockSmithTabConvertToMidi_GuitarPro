"""★フレット割当（ビーム付き Viterbi）。

01_TabForge_詳細設計書.md §9.3 / D8、02_TabForge_実装指示書.md T1-8 準拠。
ベースと同じコードでギターにも使える汎用実装（T2-2 で再利用する）。

貪欲法を採らない理由（D8）: 1音の誤りが以降のポジションを壊すため、
運指コストは経路依存として DP（Viterbi）で解く。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

Candidate = tuple[int, int]  # (string_index, fret)  index 0 = 最高音弦


@dataclass(frozen=True)
class FretConfig:
    tuning: tuple[int, ...]       # index 0 = 最高音弦の開放 MIDI
    capo: int = 0
    max_fret: int = 22
    span_max: int = 4
    w_fret: float = 0.6
    w_open: float = 0.8
    w_string: float = 0.3
    w_span: float = 1.5
    w_move: float = 1.0
    w_str_cont: float = 0.2
    w_legato: float = 0.5
    beam_width: int = 64
    candidates_per_group: int = 24
    preferred_fret: int = 7


@dataclass
class OnsetGroup:
    """同一 tick のノート集合（和音）。S6 Quantize 後の出力を束ねたもの。"""

    pitches: list[int]
    dt_beats: float = 0.0
    legato_links: set[int] = field(default_factory=set)
    warning: str | None = None


def note_candidates(pitch: int, cfg: FretConfig) -> list[Candidate]:
    out = []
    for si, open_pitch in enumerate(cfg.tuning):
        fret = pitch - open_pitch
        if fret == 0 and cfg.capo == 0:
            out.append((si, 0))
        elif cfg.capo <= fret <= cfg.max_fret:
            out.append((si, fret))
    return out


def expected_string(pitch: int, cfg: FretConfig) -> float:
    """その音高を preferred_fret 付近で押さえられる弦のインデックス（連続値）。"""
    best, best_d = 0.0, math.inf
    for si, open_pitch in enumerate(cfg.tuning):
        d = abs((pitch - open_pitch) - cfg.preferred_fret)
        if d < best_d:
            best, best_d = float(si), d
    return best


def group_span(assign: tuple[Candidate, ...]) -> int:
    frets = [f for _, f in assign if f > 0]
    return (max(frets) - min(frets)) if frets else 0


def group_center(assign: tuple[Candidate, ...]) -> float:
    frets = [f for _, f in assign if f > 0]
    return sum(frets) / len(frets) if frets else 0.0


def enumerate_group_assignments(
    pitches: list[int], cfg: FretConfig
) -> list[tuple[tuple[Candidate, ...], float]]:
    """1グループ（同一 tick の和音）の妥当な割当を emission cost 付きで列挙。"""
    per_note = [note_candidates(p, cfg) for p in pitches]
    if any(len(c) == 0 for c in per_note):
        return []  # 範囲外 → 呼び出し側で警告
    results: list[tuple[tuple[Candidate, ...], float]] = []

    def rec(i: int, acc: list[Candidate], used: set[int]) -> None:
        if i == len(per_note):
            a = tuple(acc)
            span = group_span(a)
            if span > cfg.span_max and len(a) > 1:
                # 例外: 全押弦が同一フレット（バレー）なら許可
                frets = {f for _, f in a if f > 0}
                if len(frets) > 1:
                    return
            cost = cfg.w_span * span
            for (si, fret), p in zip(a, pitches):
                cost += cfg.w_fret * abs(fret - cfg.preferred_fret) / 12.0
                if fret == 0:
                    cost -= cfg.w_open
                cost += cfg.w_string * abs(expected_string(p, cfg) - si)
            results.append((a, cost))
            return
        for si, fret in per_note[i]:
            if si in used:  # 同一弦の重複は不可
                continue
            used.add(si)
            acc.append((si, fret))
            rec(i + 1, acc, used)
            acc.pop()
            used.remove(si)

    rec(0, [], set())
    results.sort(key=lambda x: x[1])
    return results[: cfg.candidates_per_group]


def transition_cost(
    prev: tuple[Candidate, ...],
    cur: tuple[Candidate, ...],
    dt_beats: float,
    legato_links: set[int],
    cfg: FretConfig,
) -> float:
    """dt_beats: 前グループからの経過拍。legato_links: 同一弦維持が必須な音の index。"""
    c = cfg.w_move * abs(group_center(cur) - group_center(prev))
    c *= 0.3 if dt_beats > 1.0 else 1.0  # 間があれば移動は安い
    prev_strings = {si for si, _ in prev}
    changed = sum(1 for si, _ in cur if si not in prev_strings)
    c += cfg.w_str_cont * changed
    if legato_links:
        # ハンマリング/スライド候補: 同一弦を維持できなければ禁止
        if not (prev_strings & {si for si, _ in cur}):
            return math.inf
        c -= cfg.w_legato
    return c


def assign_frets(groups: list[OnsetGroup], cfg: FretConfig) -> list[tuple[Candidate, ...]]:
    """ビーム付き Viterbi。groups は時刻順。

    範囲外ノートを含むグループは `group.warning = "out_of_range"` を設定して
    スキップする（戻り値には含まれない）。呼び出し側は
    `[g for g in groups if g.warning is None]` と戻り値を zip して対応付けること。
    """
    beams: list[tuple[float, list[tuple[Candidate, ...]]]] = [(0.0, [])]
    for g in groups:
        cands = enumerate_group_assignments(g.pitches, cfg)
        if not cands:  # 範囲外ノートを含む
            g.warning = "out_of_range"
            continue
        new: list[tuple[float, list[tuple[Candidate, ...]]]] = []
        for score, path in beams:
            for a, emit in cands:
                t = 0.0
                if path:
                    t = transition_cost(path[-1], a, g.dt_beats, g.legato_links, cfg)
                    if math.isinf(t):
                        continue
                new.append((score + emit + t, path + [a]))
        if not new:  # legato 制約で全滅 → 制約を緩める
            new = [(score + emit, path + [a]) for score, path in beams for a, emit in cands]
        new.sort(key=lambda x: x[0])
        beams = new[: cfg.beam_width]
    return beams[0][1]
