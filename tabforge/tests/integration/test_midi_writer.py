from music21 import converter

from tabforge.export.midi_writer import write_midi
from tabforge.ir.models import GpDuration, TabBeat, TabIR, TabMeasure, TabNote, TabTrack

BASS_TUNING = [43, 38, 33, 28]


def _simple_tab() -> TabIR:
    measures = [
        TabMeasure(bar=1, time_signature=(4, 4), tempo=120.0, beats=[
            TabBeat(start_tick=0, duration=GpDuration(value=4), notes=[TabNote(string=4, fret=0)]),
            TabBeat(start_tick=0, duration=GpDuration(value=4), notes=[TabNote(string=3, fret=2)]),
        ]),
    ]
    return TabIR(tracks=[TabTrack(name="Bass", part="bass", tuning=BASS_TUNING,
                                   string_count=4, measures=measures)])


def test_midi_round_trip_has_expected_note_count(tmp_path):
    tab = _simple_tab()
    out = tmp_path / "score.mid"
    write_midi(tab, out)
    assert out.exists()

    score = converter.parse(str(out))
    notes = list(score.flatten().notes)
    assert len(notes) == 2
