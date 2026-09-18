"""MusicXML 生成（設計書 §10.2、実装指示書 T4-3）。

GP7/8・MuseScore・Dorico への保険経路。タブ譜情報は
``<notations><technical><string>/<fret>`` で保持する
（music21 の `articulations.StringIndication` / `FretIndication`）。
GP5 と同一の `tab.json` から生成し、両者の小節数・ノート数が一致することを
テストで保証する（`tests/integration/test_musicxml_writer.py`）。
"""
from __future__ import annotations

from pathlib import Path

from music21 import articulations, chord, meter, stream
from music21 import duration as m21duration
from music21 import note as m21note

from tabforge.ir.models import GpDuration, TabBeat, TabIR, TabTrack


def _quarter_length(gp_duration: GpDuration) -> float:
    ql = 4.0 / gp_duration.value
    if gp_duration.dotted:
        ql *= 1.5
    if gp_duration.tuplet is not None:
        n, m = gp_duration.tuplet
        ql *= m / n
    return ql


def _beat_to_music21(beat: TabBeat, tuning: list[int]):
    ql = _quarter_length(beat.duration)
    if not beat.notes:
        rest = m21note.Rest()
        rest.duration = m21duration.Duration(ql)
        return rest

    elements = []
    for tab_note in beat.notes:
        open_pitch = tuning[tab_note.string - 1]
        n = m21note.Note()
        n.pitch.midi = open_pitch + tab_note.fret
        n.articulations = [
            articulations.StringIndication(tab_note.string),
            articulations.FretIndication(tab_note.fret),
        ]
        elements.append(n)

    if len(elements) == 1:
        result = elements[0]
    else:
        result = chord.Chord([e.pitch for e in elements])
        result.articulations = [a for e in elements for a in e.articulations]
    result.duration = m21duration.Duration(ql)
    return result


def _track_to_part(track: TabTrack) -> stream.Part:
    part = stream.Part()
    part.partName = track.name
    for measure_ir in track.measures:
        m21_measure = stream.Measure(number=measure_ir.bar)
        if measure_ir.bar == 1:
            numerator, denominator = measure_ir.time_signature
            m21_measure.timeSignature = meter.TimeSignature(f"{numerator}/{denominator}")
        if not measure_ir.beats:
            numerator, denominator = measure_ir.time_signature
            rest = m21note.Rest()
            rest.duration = m21duration.Duration(4.0 * numerator / denominator)
            m21_measure.append(rest)
        else:
            for beat in measure_ir.beats:
                m21_measure.append(_beat_to_music21(beat, track.tuning))
        part.append(m21_measure)
    return part


def write_musicxml(tab: TabIR, out: Path) -> None:
    score = stream.Score()
    for track in tab.tracks:
        score.append(_track_to_part(track))
    out.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(out))
