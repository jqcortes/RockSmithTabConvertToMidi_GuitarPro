from tabforge.export.ascii_tab import render_ascii_tab
from tabforge.ir.models import GpDuration, TabBeat, TabIR, TabMeasure, TabNote, TabTrack

BASS_TUNING = [43, 38, 33, 28]


def test_render_shows_track_name_and_frets():
    measures = [
        TabMeasure(bar=1, time_signature=(4, 4), tempo=120.0, beats=[
            TabBeat(start_tick=0, duration=GpDuration(value=4), notes=[TabNote(string=4, fret=0)]),
            TabBeat(start_tick=0, duration=GpDuration(value=4), notes=[TabNote(string=3, fret=12)]),
        ]),
    ]
    tab = TabIR(tracks=[TabTrack(name="Bass", part="bass", tuning=BASS_TUNING, string_count=4, measures=measures)])
    text = render_ascii_tab(tab)
    assert "Bass" in text
    assert "12" in text
    lines = text.splitlines()
    assert len(lines) == 5  # ヘッダ + 4弦分


def test_empty_measure_renders_dashes_only():
    tab = TabIR(tracks=[TabTrack(
        name="Bass", part="bass", tuning=BASS_TUNING, string_count=4,
        measures=[TabMeasure(bar=1, time_signature=(4, 4), tempo=120.0, beats=[])],
    )])
    text = render_ascii_tab(tab)
    for line in text.splitlines()[1:]:
        assert "-" in line
