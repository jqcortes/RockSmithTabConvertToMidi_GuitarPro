from tabforge.config import DisentangleConfig
from tabforge.ir.models import Beat, ChordsIR, GridIR, Note, NoteFeatures, NotesIR, TimeSignature
from tabforge.stages.s5_disentangle import (
    classify_lead_rhythm,
    classify_phase_a,
    count_part_switches,
    hmm_smooth_lead_rhythm,
    postprocess_regions,
)

BPM = 120.0
BEAT_LEN = 0.5


def _grid(n_beats: int = 32) -> GridIR:
    beats = [Beat(t=i * BEAT_LEN, beat_in_bar=(i % 4) + 1, bar=i // 4 + 1, is_downbeat=i % 4 == 0)
             for i in range(n_beats)]
    return GridIR(sample_rate=44100, duration_sec=n_beats * BEAT_LEN, tempo_bpm_global=BPM,
                  time_signature=TimeSignature(numerator=4, denominator=4), beats=beats)


def _no_chords() -> ChordsIR:
    return ChordsIR(source="none", segments=[])


def _note(id_, pitch, instrument) -> Note:
    return Note(id=id_, onset=0.0, offset=0.5, pitch=pitch, instrument=instrument, conf=1.0)


def test_bass_instrument_always_classified_as_bass():
    notes = NotesIR(notes=[_note("a", 60, "electric_bass")])
    parts = classify_phase_a(notes)
    assert parts.assignments[0].part == "bass"
    assert parts.part_stats["bass"] == 1


def test_low_pitch_non_bass_instrument_classified_as_bass():
    notes = NotesIR(notes=[_note("a", 40, "distorted_electric_guitar")])
    parts = classify_phase_a(notes)
    assert parts.assignments[0].part == "bass"


def test_high_pitch_guitar_note_unassigned_in_phase_a():
    notes = NotesIR(notes=[_note("a", 64, "distorted_electric_guitar")])
    parts = classify_phase_a(notes)
    assert parts.assignments[0].part == "unassigned"
    assert parts.part_stats["unassigned"] == 1


def test_hmm_smoothing_reduces_switch_count():
    scores = [2, 2, 2, -2, 2, 2, 2, 2, -2, 2, 2, 2]
    naive = ["lead" if s > 0 else "rhythm" for s in scores]
    naive_switches = count_part_switches(naive)

    smoothed = hmm_smooth_lead_rhythm(scores, stay_prob=0.92)
    smoothed_switches = count_part_switches(smoothed)

    assert smoothed_switches < naive_switches


def test_hmm_smoothing_disabled_equivalent_is_noisier():
    # stay_prob=0.5 (実質スムージング無し) だと素の閾値判定に近くなる
    scores = [2, 2, 2, -2, 2, 2, 2, 2, -2, 2, 2, 2]
    unsmoothed_like = hmm_smooth_lead_rhythm(scores, stay_prob=0.5)
    smoothed = hmm_smooth_lead_rhythm(scores, stay_prob=0.92)
    assert count_part_switches(smoothed) < count_part_switches(unsmoothed_like)


def test_postprocess_merges_isolated_short_lead_region():
    sixteenth = BEAT_LEN / 4
    notes = [Note(id=f"n{i}", onset=i * sixteenth, offset=(i + 1) * sixteenth, pitch=64,
                   instrument="guitar") for i in range(4)]
    clusters = [[n] for n in notes]
    # 2つ目のクラスタだけ孤立した lead (16分 = 0.25拍 < 1拍) → まず rhythm に吸収され、
    # その後「rhythm 区間内の孤立単音」規則により unassigned として要レビューに回る。
    states = ["rhythm", "lead", "rhythm", "rhythm"]
    result = postprocess_regions(states, clusters, beat_len=BEAT_LEN)
    assert result[0] == "rhythm"
    assert result[1] == "unassigned"
    assert result[2] == "rhythm"
    assert result[3] == "rhythm"


def test_postprocess_flags_isolated_monophonic_note_in_rhythm_as_unassigned():
    notes = [Note(id=f"n{i}", onset=i * BEAT_LEN, offset=(i + 1) * BEAT_LEN, pitch=64,
                   instrument="guitar") for i in range(3)]
    clusters = [[notes[0]], [notes[1]], [notes[2]]]
    states = ["rhythm", "rhythm", "rhythm"]
    result = postprocess_regions(states, clusters, beat_len=BEAT_LEN)
    assert result[1] == "unassigned"


def test_classify_lead_rhythm_splits_solo_from_chords():
    grid = _grid()
    notes = []
    # 小節1-2: 3声パワーコード刻み(強制rhythm)
    for beat in range(8):
        onset = beat * BEAT_LEN
        for pitch in (40, 47, 52):
            notes.append(Note(id=f"chord{beat}_{pitch}", onset=onset, offset=onset + BEAT_LEN,
                               pitch=pitch, instrument="distorted_electric_guitar"))
    # 小節3-4: 単音の16分ソロ(高音域・速い・非和声音がち)
    sixteenth = BEAT_LEN / 4
    for i in range(32):
        onset = 8 * BEAT_LEN + i * sixteenth
        notes.append(Note(id=f"lead{i}", onset=onset, offset=onset + sixteenth,
                           pitch=76 + (i % 3), instrument="distorted_electric_guitar"))

    assignments = classify_lead_rhythm(notes, _no_chords(), grid, DisentangleConfig())
    by_id = {a.note_id: a.part for a in assignments}

    chord_parts = {by_id[f"chord{b}_{p}"] for b in range(8) for p in (40, 47, 52)}
    assert chord_parts == {"rhythm"}

    lead_parts = [by_id[f"lead{i}"] for i in range(32)]
    assert lead_parts.count("lead") > len(lead_parts) * 0.7


def test_split_lead_tracks_separates_by_register_and_pan():
    from tabforge.stages.s5_disentangle import name_lead_tracks, split_lead_tracks

    # 高音域・右寄りのグループ と 低音域・左寄りのグループ
    high_notes = [Note(id=f"hi{i}", onset=i * 0.5, offset=i * 0.5 + 0.2, pitch=76,
                        instrument="guitar", pan=0.7) for i in range(4)]
    low_notes = [Note(id=f"lo{i}", onset=i * 0.5 + 8.0, offset=i * 0.5 + 8.2, pitch=52,
                       instrument="guitar", pan=-0.7) for i in range(4)]
    all_notes = high_notes + low_notes

    features = {}
    for n in high_notes:
        features[n.id] = NoteFeatures(register=1.0, ioi=0.5, pan=0.7)
    for n in low_notes:
        features[n.id] = NoteFeatures(register=0.0, ioi=0.5, pan=-0.7)

    assignment = split_lead_tracks(all_notes, features, k=2)
    high_labels = {assignment[n.id] for n in high_notes}
    low_labels = {assignment[n.id] for n in low_notes}
    assert high_labels != low_labels
    assert len(high_labels) == 1 and len(low_labels) == 1

    by_label: dict[int, list[Note]] = {}
    for n in all_notes:
        by_label.setdefault(assignment[n.id], []).append(n)
    names = name_lead_tracks(by_label, features)
    assert set(names.values()) == {"Gtr L", "Gtr R"}


def test_split_lead_tracks_noop_for_k_1():
    from tabforge.stages.s5_disentangle import split_lead_tracks

    notes = [Note(id="a", onset=0, offset=0.5, pitch=64, instrument="guitar")]
    assignment = split_lead_tracks(notes, {}, k=1)
    assert assignment == {"a": 0}
