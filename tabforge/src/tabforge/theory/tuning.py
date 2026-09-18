"""チューニング／カポ推定（設計書 §9.2、実装指示書 T2-1）。

`tuning` は常に index 0 = 1弦（最高音）で保持する（設計書 §10.1 の規約）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

MAX_SEMITONE_SHIFT = 6
OUT_OF_RANGE_THRESHOLD = 0.02  # r > 2%


@dataclass(frozen=True)
class TuningEstimate:
    tuning: tuple[int, ...]         # 推定チューニング（index0=最高音弦）
    label: str                      # 例: "Eb Standard (半音下げ)"
    semitone_shift: int             # 0-6
    drop_lowest: bool               # 最低弦をさらに全音下げる (Drop D 系)
    out_of_range_rate: float
    conf: float
    alternatives: list[tuple[str, float]] = field(default_factory=list)


def _out_of_range_rate(pitches: list[int], tuning: tuple[int, ...]) -> float:
    if not pitches:
        return 0.0
    floor = min(tuning)
    below = sum(1 for p in pitches if p < floor)
    return below / len(pitches)


def _shifted(base: tuple[int, ...], shift: int, drop_lowest: bool) -> tuple[int, ...]:
    tuning = tuple(p - shift for p in base)
    if drop_lowest:
        tuning = tuning[:-1] + (tuning[-1] - 2,)
    return tuning


def _label(shift: int, drop_lowest: bool) -> str:
    names = {0: "E", 1: "Eb", 2: "D", 3: "C#", 4: "C", 5: "B", 6: "Bb"}
    base_label = f"{names.get(shift, f'-{shift}st')} Standard"
    if shift > 0:
        base_label += f" (半音下げ x{shift})"
    if drop_lowest:
        base_label += " + Drop"
    return base_label


def estimate_tuning(
    pitches: list[int], base: tuple[int, ...], kind: Literal["guitar", "bass"]
) -> TuningEstimate:
    """半音下げ系 (k=1..6) と Drop 系（最低弦のみ -2）を評価し、
    範囲外ノート率が最小の候補を返す。conf と代替候補も返す。
    """
    standard_rate = _out_of_range_rate(pitches, base)
    if standard_rate <= OUT_OF_RANGE_THRESHOLD:
        return TuningEstimate(
            tuning=base, label=_label(0, False), semitone_shift=0, drop_lowest=False,
            out_of_range_rate=standard_rate, conf=1.0 - standard_rate,
            alternatives=[(_label(0, False), standard_rate)],
        )

    # Step 1: 全弦を -k した仮チューニング (k=1..6) を評価し、範囲外ノート率が
    # 閾値以下になる最小の k を採用する（閾値を満たす k が無ければ誤差最小の k）。
    full_shift_candidates = [
        (shift, _out_of_range_rate(pitches, _shifted(base, shift, False)))
        for shift in range(1, MAX_SEMITONE_SHIFT + 1)
    ]
    under_threshold = [c for c in full_shift_candidates if c[1] <= OUT_OF_RANGE_THRESHOLD]
    best_shift, best_rate = min(under_threshold or full_shift_candidates, key=lambda c: (c[1], c[0]))
    best_tuning = _shifted(base, best_shift, False)
    best_drop = False

    alternatives = [(_label(0, False), standard_rate)]
    alternatives += [(_label(s, False), r) for s, r in full_shift_candidates]

    # Step 2: k=2（全音下げ）が採用された場合のみ、6弦（最低弦）だけを
    # 下げる Drop D 系のほうが同等以上に良くないか確認する。
    if best_shift == 2:
        drop_tuning = _shifted(base, 0, True)
        drop_rate = _out_of_range_rate(pitches, drop_tuning)
        alternatives.append((_label(0, True), drop_rate))
        if drop_rate <= best_rate:
            best_shift, best_drop, best_tuning, best_rate = 0, True, drop_tuning, drop_rate

    return TuningEstimate(
        tuning=best_tuning,
        label=_label(best_shift, best_drop),
        semitone_shift=best_shift,
        drop_lowest=best_drop,
        out_of_range_rate=best_rate,
        conf=max(0.0, 1.0 - best_rate),
        alternatives=alternatives,
    )


def estimate_capo(frets_by_note: list[int]) -> int:
    """フレット出現ヒストグラムの最小値が 2 以上なら、その値を capo として提案する。"""
    if not frets_by_note:
        return 0
    f_min = min(frets_by_note)
    return f_min if f_min >= 2 else 0


def detect_5string_bass(pitches: list[int], threshold: float = 0.01) -> bool:
    """pitch < 28 (E1, 4弦ベース最低音) が有意に存在するかどうか。"""
    if not pitches:
        return False
    below = sum(1 for p in pitches if p < 28)
    return (below / len(pitches)) > threshold
