"""秒 ↔ tick ↔ GP Duration の変換（設計書 §9.1 / 実装指示書 T1-7）。

GP Duration の value は「全音符の何分の1か」(1,2,4,8,16,32,64)。
dotted は 1.5倍、tuplet=(n, m) は「m拍分の時間に n個」を意味し、
1個あたりの長さは基準の m/n 倍になる（3連符=(3,2), 5連符=(5,4) 等）。
"""
from __future__ import annotations

import math

from tabforge.ir.models import GpDuration

VALID_VALUES: tuple[int, ...] = (1, 2, 4, 8, 16, 32, 64)
SUPPORTED_TUPLETS: tuple[tuple[int, int] | None, ...] = (None, (3, 2), (5, 4))


def seconds_to_ticks(seconds: float, bpm: float, ppq: int) -> int:
    return round(seconds * ppq * bpm / 60.0)


def ticks_to_seconds(ticks: int, bpm: float, ppq: int) -> float:
    return ticks * 60.0 / (ppq * bpm)


def duration_ticks(value: int, ppq: int, dotted: bool = False, tuplet: tuple[int, int] | None = None) -> float:
    """1つの GpDuration が表す長さ（tick, 実数）。"""
    base = ppq * 4.0 / value
    if dotted:
        base *= 1.5
    if tuplet is not None:
        n, m = tuplet
        base *= m / n
    return base


def to_gp_duration(ticks: float, ppq: int) -> GpDuration:
    """誤差最小の単一 GpDuration を返す（表現できない長さでも最良近似を返す）。

    複数に分割すべきか（表現できないほど誤差が大きいか）の判定は
    `quantize_to_gp_durations` 側で行う。
    """
    best: GpDuration | None = None
    best_err = math.inf
    for value in VALID_VALUES:
        for dotted in (False, True):
            for tuplet in SUPPORTED_TUPLETS:
                candidate_ticks = duration_ticks(value, ppq, dotted, tuplet)
                err = abs(candidate_ticks - ticks)
                if err < best_err - 1e-9:
                    best_err = err
                    best = GpDuration(value=value, dotted=dotted, tuplet=tuplet)
    assert best is not None
    return best


def quantize_to_gp_durations(
    ticks: float, ppq: int, tolerance_ticks: float = 1.0
) -> list[GpDuration]:
    """ticks を GpDuration の列に変換する。

    単一の GpDuration で `tolerance_ticks` 以内に収まればそれを1件返す。
    収まらない場合は tie で連結する前提の分割リストを返す（大きい方から貪欲に埋める）。
    """
    single = to_gp_duration(ticks, ppq)
    single_ticks = duration_ticks(single.value, ppq, single.dotted, single.tuplet)
    if abs(single_ticks - ticks) <= tolerance_ticks:
        return [single]

    remaining = ticks
    result: list[GpDuration] = []
    all_options = [
        (duration_ticks(value, ppq, dotted, tuplet), GpDuration(value=value, dotted=dotted, tuplet=tuplet))
        for value in VALID_VALUES
        for dotted in (False, True)
        for tuplet in SUPPORTED_TUPLETS
    ]
    guard = 0
    while remaining > tolerance_ticks and guard < 32:
        guard += 1
        fitting = [(t, gd) for t, gd in all_options if t <= remaining + tolerance_ticks]
        if not fitting:
            break
        t, gd = max(fitting, key=lambda item: item[0])
        result.append(gd)
        remaining -= t
    return result or [single]
