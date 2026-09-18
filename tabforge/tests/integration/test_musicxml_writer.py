from music21 import converter

from tabforge.export.musicxml_writer import write_musicxml
from tabforge.ir.models import GpDuration, TabBeat, TabIR, TabMeasure, TabNote, TabTrack

BASS_TUNING = [43, 38, 33, 28]  # G2 D2 A1 E1


def _tab_with_chord_and_rest() -> TabIR:
    measures = [
        TabMeasure(
            bar=1, time_signature=(4, 4), tempo=120.0,
            beats=[
                TabBeat(start_tick=0, duration=GpDuration(value=4),
                        notes=[TabNote(string=4, fret=0)]),
                TabBeat(start_tick=0, duration=GpDuration(value=4),
                        notes=[TabNote(string=3, fret=2), TabNote(string=4, fret=2)]),
            ],
        ),
        TabMeasure(bar=2, time_signature=(4, 4), tempo=120.0, beats=[]),  # 空小節
    ]
    return TabIR(tracks=[TabTrack(name="Bass", part="bass", tuning=BASS_TUNING,
                                   string_count=4, measures=measures)])


def test_musicxml_measure_and_note_count_matches_tab_json(tmp_path):
    tab = _tab_with_chord_and_rest()
    out = tmp_path / "score.musicxml"
    write_musicxml(tab, out)
    assert out.exists()

    score = converter.parse(str(out))
    part = score.parts[0]
    measures = list(part.getElementsByClass("Measure"))
    assert len(measures) == 2  # tab.json と同じ小節数

    total_notes = 0
    for m in measures:
        for el in m.notesAndRests:
            if el.isRest:
                continue
            if el.isChord:
                total_notes += len(el.pitches)
            else:
                total_notes += 1
    assert total_notes == 3  # 1音 + 2音和音 = 3


def test_musicxml_empty_measure_becomes_rest(tmp_path):
    tab = _tab_with_chord_and_rest()
    out = tmp_path / "score.musicxml"
    write_musicxml(tab, out)
    score = converter.parse(str(out))
    measures = list(score.parts[0].getElementsByClass("Measure"))
    second = measures[1]
    assert all(el.isRest for el in second.notesAndRests)
