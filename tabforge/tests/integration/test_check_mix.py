import soundfile as sf

from tabforge.export.auralize import write_check_mix
from tabforge.ir.models import GpDuration, TabBeat, TabIR, TabMeasure, TabNote, TabTrack

BASS_TUNING = [43, 38, 33, 28]


def test_write_check_mix_produces_stereo_wav(tmp_path, synthetic_riff_wav):
    measures = [
        TabMeasure(bar=1, time_signature=(4, 4), tempo=120.0, beats=[
            TabBeat(start_tick=0, duration=GpDuration(value=4), notes=[TabNote(string=4, fret=0)]),
        ]),
    ]
    tab = TabIR(tracks=[TabTrack(name="Bass", part="bass", tuning=BASS_TUNING,
                                  string_count=4, measures=measures)])
    out = tmp_path / "check_mix.wav"
    write_check_mix(tab, synthetic_riff_wav, out)

    assert out.exists()
    info = sf.info(str(out))
    assert info.channels == 2
