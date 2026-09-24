"""eval/note_metrics.py のテスト。

`eval/` はインストールされるパッケージの外（スタンドアロンスクリプト置き場）
のため、sys.path に追加してから import する。
"""
from __future__ import annotations

import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[2] / "eval"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

from note_metrics import onset_f1, onset_pitch_f1

from tabforge.ir.models import Note


def _note(id_, onset, offset, pitch) -> Note:
    return Note(id=id_, onset=onset, offset=offset, pitch=pitch, instrument="guitar")


def test_onset_f1_perfect_match():
    notes = [_note("a", 1.0, 1.5, 64), _note("b", 2.0, 2.4, 67)]
    result = onset_f1(notes, notes)
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1 == 1.0


def test_onset_f1_within_tolerance_still_matches():
    ref = [_note("a", 1.0, 1.5, 64)]
    est = [_note("a", 1.03, 1.5, 64)]  # 30ms ずれ (tolerance=50ms)
    result = onset_f1(ref, est, tolerance_sec=0.05)
    assert result.f1 == 1.0


def test_onset_f1_outside_tolerance_misses():
    ref = [_note("a", 1.0, 1.5, 64)]
    est = [_note("a", 1.3, 1.5, 64)]  # 300ms ずれ
    result = onset_f1(ref, est, tolerance_sec=0.05)
    assert result.f1 == 0.0


def test_onset_pitch_f1_requires_correct_pitch():
    ref = [_note("a", 1.0, 1.5, 64)]
    matching_pitch = [_note("a", 1.0, 1.5, 64)]
    wrong_pitch = [_note("a", 1.0, 1.5, 76)]  # 1オクターブ違い

    assert onset_pitch_f1(ref, matching_pitch).f1 == 1.0
    assert onset_pitch_f1(ref, wrong_pitch).f1 == 0.0


def test_empty_inputs_do_not_crash():
    result = onset_f1([], [])
    assert result.f1 == 0.0
