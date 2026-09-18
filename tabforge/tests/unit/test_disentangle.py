from tabforge.ir.models import Note, NotesIR
from tabforge.stages.s5_disentangle import classify_phase_a


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
