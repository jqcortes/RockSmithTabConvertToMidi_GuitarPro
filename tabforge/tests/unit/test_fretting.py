from tabforge.arrange.fretting import (
    FretConfig,
    OnsetGroup,
    assign_frets,
    enumerate_group_assignments,
    group_span,
)

# index 0 = 1弦（最高音）
GUITAR_STANDARD = (64, 59, 55, 50, 45, 40)  # E4 B3 G3 D3 A2 E2
BASS_STANDARD = (43, 38, 33, 28)  # G2 D2 A1 E1


def _cfg(**overrides) -> FretConfig:
    base = {"tuning": GUITAR_STANDARD, "max_fret": 22, "span_max": 4}
    base.update(overrides)
    return FretConfig(**base)


def test_c_major_scale_stays_in_one_position():
    scale = [60, 62, 64, 65, 67, 69, 71, 72]  # C4..C5
    groups = [OnsetGroup(pitches=[p], dt_beats=0.5) for p in scale]
    cfg = _cfg()
    path = assign_frets(groups, cfg)
    assert all(g.warning is None for g in groups)
    frets = [assign[0][1] for assign in path]
    assert max(frets) - min(frets) <= 5


def test_open_e_major_chord_reproduces_standard_voicing():
    # E2 B2 E3 G#3 B3 E4 (低い順)。frets 0,2,2,1,0,0 が既知の定型フォーム。
    pitches = [40, 47, 52, 56, 59, 64]
    groups = [OnsetGroup(pitches=pitches)]
    cfg = _cfg()
    path = assign_frets(groups, cfg)
    assert groups[0].warning is None
    assign = dict(path[0])  # string_index -> fret
    assert assign == {5: 0, 4: 2, 3: 2, 2: 1, 1: 0, 0: 0}


def test_open_g_major_chord_reproduces_standard_voicing():
    pitches = [43, 47, 50, 55, 59, 67]  # G2 B2 D3 G3 B3 G4, frets 3,2,0,0,0,3
    groups = [OnsetGroup(pitches=pitches)]
    cfg = _cfg()
    path = assign_frets(groups, cfg)
    assert groups[0].warning is None
    assign = dict(path[0])
    assert assign == {5: 3, 4: 2, 3: 0, 2: 0, 1: 0, 0: 3}


def test_open_c_major_chord_reproduces_standard_voicing():
    pitches = [48, 52, 55, 60, 64]  # C3 E3 G3 C4 E4, frets x,3,2,0,1,0 (5弦から)
    groups = [OnsetGroup(pitches=pitches)]
    cfg = _cfg()
    path = assign_frets(groups, cfg)
    assert groups[0].warning is None
    assign = dict(path[0])
    assert assign == {4: 3, 3: 2, 2: 0, 1: 1, 0: 0}


def test_span_violation_rejected_unless_barre():
    # 1フレットと10フレットの2音は span_max=4 を超えるため単純な非バレーでは不可
    cfg = _cfg(span_max=4)
    results = enumerate_group_assignments([41, 74], cfg)  # F2/(low), D5(high) など極端な例
    for assign, _cost in results:
        span = group_span(assign)
        frets = {f for _, f in assign if f > 0}
        assert span <= cfg.span_max or len(frets) <= 1


def test_legato_forces_same_string():
    cfg = _cfg()
    groups = [
        OnsetGroup(pitches=[50], dt_beats=0.0),          # D3 (3弦開放)
        OnsetGroup(pitches=[52], dt_beats=0.1, legato_links={0}),  # ハンマリング候補
    ]
    path = assign_frets(groups, cfg)
    assert groups[0].warning is None and groups[1].warning is None
    prev_string = path[0][0][0]
    cur_string = path[1][0][0]
    assert prev_string == cur_string


def test_out_of_range_group_flagged_and_excluded_from_path():
    cfg = _cfg(max_fret=22)
    groups = [
        OnsetGroup(pitches=[60]),
        OnsetGroup(pitches=[200]),  # 範囲外
        OnsetGroup(pitches=[62]),
    ]
    path = assign_frets(groups, cfg)
    in_range = [g for g in groups if g.warning is None]
    assert len(in_range) == 2
    assert groups[1].warning == "out_of_range"
    assert len(path) == 2


def test_bass_position_jumps_under_threshold_per_100_notes():
    cfg = FretConfig(tuning=BASS_STANDARD, max_fret=24, span_max=4)
    # 2オクターブの walking bass 相当を12回繰り返し、100音規模で検証
    walk = [28, 31, 33, 35, 38, 40, 43, 45]
    pitches = (walk * 13)[:104]
    groups = [OnsetGroup(pitches=[p], dt_beats=0.5) for p in pitches]
    path = assign_frets(groups, cfg)
    assert all(g.warning is None for g in groups)
    from itertools import pairwise

    centers = [sum(f for _, f in a) / len(a) for a in path]
    jumps = sum(1 for a, b in pairwise(centers) if abs(b - a) > 5)
    assert jumps < 3 * (len(pitches) / 100)
