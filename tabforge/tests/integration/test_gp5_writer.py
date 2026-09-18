import guitarpro as gp

from tabforge.export.gp5_writer import write_gp5
from tabforge.ir.models import (
    BendEffect,
    GpDuration,
    NoteEffects,
    TabBeat,
    TabIR,
    TabMeasure,
    TabNote,
    TabTrack,
)

BASS_TUNING = [43, 38, 33, 28]  # G2 D2 A1 E1 (index0 = 最高音弦)


def _bass_tab() -> TabIR:
    measures = []
    for bar in range(1, 3):
        beat = TabBeat(
            start_tick=0,
            duration=GpDuration(value=4),
            notes=[TabNote(string=4, fret=0, effects=NoteEffects())],  # 開放E1
        )
        beat2 = TabBeat(
            start_tick=480,
            duration=GpDuration(value=4),
            notes=[
                TabNote(
                    string=3, fret=2,
                    effects=NoteEffects(bend=BendEffect(points=[(0, 0), (12, 4)])),
                )
            ],
        )
        measures.append(TabMeasure(bar=bar, time_signature=(4, 4), tempo=120.0, beats=[beat, beat2]))

    return TabIR(
        tracks=[
            TabTrack(name="Bass", part="bass", tuning=BASS_TUNING, string_count=4, measures=measures)
        ]
    )


def test_gp5_round_trip_preserves_notes_strings_frets(tmp_path):
    tab = _bass_tab()
    out_path = tmp_path / "score.gp5"
    write_gp5(tab, out_path)
    assert out_path.exists()

    song = gp.parse(str(out_path))
    track = song.tracks[0]

    assert track.strings[0].number == 1
    assert [s.value for s in track.strings] == BASS_TUNING

    all_notes = [n for m in track.measures for v in m.voices for b in v.beats for n in b.notes]
    assert len(all_notes) == 4  # 2小節 x 2音

    frets_strings = {(n.string, n.value) for n in all_notes}
    assert (4, 0) in frets_strings
    assert (3, 2) in frets_strings

    bent_notes = [n for n in all_notes if n.effect.bend is not None]
    assert len(bent_notes) == 2
    assert [(p.position, p.value) for p in bent_notes[0].effect.bend.points] == [(0, 0), (12, 4)]
