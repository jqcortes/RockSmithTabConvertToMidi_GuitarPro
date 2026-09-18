import pytest

from tabforge.theory.chords import QUALITY_INTERVALS, ChordLabelError, parse_chord_label


def test_no_chord_label():
    info = parse_chord_label("N")
    assert info.root is None
    assert info.pitch_classes == ()


def test_a_min7_matches_design_doc_example():
    info = parse_chord_label("A:min7")
    assert info.root == 9
    assert info.quality == "min7"
    assert set(info.pitch_classes) == {9, 0, 4, 7}


def test_slash_chord_scale_degree_matches_design_doc_example():
    # D:maj/5 -> root=D(2), bass=A(9) (設計書 §5.2 の例)
    info = parse_chord_label("D:maj/5")
    assert info.root == 2
    assert info.bass == 9
    assert set(info.pitch_classes) == {2, 6, 9}


def test_bare_root_defaults_to_major():
    info = parse_chord_label("C")
    assert info.quality == "maj"
    assert set(info.pitch_classes) == {0, 4, 7}


def test_unknown_root_raises():
    with pytest.raises(ChordLabelError):
        parse_chord_label("H:maj")


def test_unknown_quality_raises():
    with pytest.raises(ChordLabelError):
        parse_chord_label("C:bogus")


@pytest.mark.parametrize("quality", sorted(QUALITY_INTERVALS))
def test_all_qualities_parse_for_c_root(quality):
    info = parse_chord_label(f"C:{quality}")
    assert info.root == 0
    assert 0 in info.pitch_classes  # ルート音は必ず含まれる
    assert len(info.pitch_classes) == len(set(QUALITY_INTERVALS[quality]))
