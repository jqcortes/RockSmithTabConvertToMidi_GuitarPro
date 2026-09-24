"""eval/guitarset_fretting.py のテスト（実データ非依存の評価ロジック部分）。"""
from __future__ import annotations

import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[2] / "eval"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

from guitarset_fretting import (
    GroundTruthNote,
    _our_index_to_guitarset_string,
    evaluate_fretting,
)

from tabforge.arrange.fretting import FretConfig, OnsetGroup, assign_frets

GUITAR_STANDARD = (64, 59, 55, 50, 45, 40)  # E4 B3 G3 D3 A2 E2


def test_index_conversion_reverses_order():
    assert _our_index_to_guitarset_string(0, 6) == 5  # 1弦(最高音) -> guitarset 5
    assert _our_index_to_guitarset_string(5, 6) == 0  # 6弦(最低音) -> guitarset 0


def test_self_consistent_ground_truth_scores_perfect_accuracy():
    # assign_frets 自身の出力をそのまま正解として与えれば 100% になるはず
    # (評価ロジック自体のテスト。アルゴリズムの正しさは test_fretting.py が担保)
    pitches = [60, 62, 64, 65, 67, 69, 71, 72]  # C major scale
    cfg = FretConfig(tuning=GUITAR_STANDARD)
    groups = [OnsetGroup(pitches=[p], dt_beats=0.5) for p in pitches]
    assignments = assign_frets(groups, cfg)

    n_strings = len(GUITAR_STANDARD)
    ground_truth = []
    for i, (pitch, assign) in enumerate(zip(pitches, assignments, strict=True)):
        our_index, fret = assign[0]
        gt_string = n_strings - 1 - our_index
        ground_truth.append(GroundTruthNote(onset=float(i), offset=float(i) + 0.5, pitch=pitch,
                                             string=gt_string, fret=fret))

    result = evaluate_fretting(ground_truth, cfg)
    assert result["string_accuracy"] == 1.0
    assert result["fret_accuracy"] == 1.0
    assert result["n_in_range"] == len(pitches)


def test_wrong_ground_truth_scores_less_than_perfect():
    pitches = [60, 62, 64]
    cfg = FretConfig(tuning=GUITAR_STANDARD)
    groups = [OnsetGroup(pitches=[p], dt_beats=0.5) for p in pitches]
    assignments = assign_frets(groups, cfg)

    n_strings = len(GUITAR_STANDARD)
    ground_truth = []
    for i, (pitch, assign) in enumerate(zip(pitches, assignments, strict=True)):
        our_index, fret = assign[0]
        gt_string = n_strings - 1 - our_index
        # わざと1つ目のノートだけ間違ったフレットにする
        wrong_fret = fret + 5 if i == 0 else fret
        ground_truth.append(GroundTruthNote(onset=float(i), offset=float(i) + 0.5, pitch=pitch,
                                             string=gt_string, fret=wrong_fret))

    result = evaluate_fretting(ground_truth, cfg)
    assert result["fret_accuracy"] < 1.0


def test_chord_ground_truth_grouped_by_onset():
    # E major open chord: 単一オンセットの和音として1グループで解かれるべき
    pitches = [40, 47, 52, 56, 59, 64]
    cfg = FretConfig(tuning=GUITAR_STANDARD)
    expected = {40: (5, 0), 47: (4, 2), 52: (3, 2), 56: (2, 1), 59: (1, 0), 64: (0, 0)}
    n_strings = len(GUITAR_STANDARD)
    ground_truth = [
        GroundTruthNote(onset=0.0, offset=0.5, pitch=p,
                         string=n_strings - 1 - expected[p][0], fret=expected[p][1])
        for p in pitches
    ]
    result = evaluate_fretting(ground_truth, cfg)
    assert result["string_accuracy"] == 1.0
    assert result["fret_accuracy"] == 1.0


def test_empty_ground_truth():
    cfg = FretConfig(tuning=GUITAR_STANDARD)
    result = evaluate_fretting([], cfg)
    assert result["n_notes"] == 0
