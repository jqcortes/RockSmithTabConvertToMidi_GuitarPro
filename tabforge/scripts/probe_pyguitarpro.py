"""⚠検証スクリプト（T0-3）。

最小の .gp5 を手書き生成 → 再パース → 一致確認する。
実行結果（確定した API の呼び出し方）は export/gp5_writer.py の docstring に反映済み。

使い方:
    uv run python scripts/probe_pyguitarpro.py /tmp/probe.gp5
"""
from __future__ import annotations

import sys
from pathlib import Path

import guitarpro as gp


def build_probe_song() -> gp.Song:
    song = gp.Song(title="TabForge Probe", tempo=120)
    song.tracks = []

    track = gp.Track(song, number=1, name="Probe Guitar")
    # GuitarString.number: 1 = 1弦(最高音)。value は MIDI ノート番号。
    track.strings = [
        gp.GuitarString(1, 64), gp.GuitarString(2, 59), gp.GuitarString(3, 55),
        gp.GuitarString(4, 50), gp.GuitarString(5, 45), gp.GuitarString(6, 40),
    ]
    song.tracks.append(track)

    song.measureHeaders = []
    for i in range(4):
        header = gp.MeasureHeader(number=i + 1, start=960 * 4 * i + 1)
        header.timeSignature = gp.TimeSignature(numerator=4, denominator=gp.Duration(value=4))
        song.measureHeaders.append(header)

    track.measures = []
    for header in song.measureHeaders:
        measure = gp.Measure(track, header)
        voice = measure.voices[0]
        voice.beats = []

        # 1拍目: 単音 (12フレット、1弦) + チョーキング
        beat1 = gp.Beat(voice)
        beat1.duration = gp.Duration(value=4)
        note1 = gp.Note(beat1, value=12, string=1, type=gp.NoteType.normal)
        note1.effect.bend = gp.BendEffect(
            type=gp.BendType.bend,
            points=[gp.BendPoint(position=0, value=0), gp.BendPoint(position=12, value=4)],
        )
        beat1.notes = [note1]
        voice.beats.append(beat1)

        # 2拍目: 開放弦の和音 (E major 相当)
        beat2 = gp.Beat(voice)
        beat2.duration = gp.Duration(value=4)
        chord_frets = {6: 0, 5: 2, 4: 2, 3: 1, 2: 0, 1: 0}
        chord_notes = []
        for string_number, fret in chord_frets.items():
            n = gp.Note(beat2, value=fret, string=string_number, type=gp.NoteType.normal)
            chord_notes.append(n)
        beat2.notes = chord_notes
        voice.beats.append(beat2)

        # 3-4拍目: 休符 Beat（空小節での表示崩れ確認）
        for _ in range(2):
            rest = gp.Beat(voice)
            rest.duration = gp.Duration(value=4)
            rest.status = gp.BeatStatus.rest
            voice.beats.append(rest)

        measure.voices[0] = voice
        track.measures.append(measure)

    return song


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/tabforge_probe.gp5")
    song = build_probe_song()
    gp.write(song, str(out_path), version=(5, 1, 0))
    print(f"wrote {out_path}")

    reparsed = gp.parse(str(out_path))
    track = reparsed.tracks[0]
    assert track.strings[0].number == 1, "GuitarString.number: 1=最高音弦のはず"
    total_notes = sum(len(b.notes) for m in track.measures for v in m.voices for b in v.beats)
    print(f"re-parsed OK: measures={len(track.measures)} total_notes={total_notes}")

    first_note = track.measures[0].voices[0].beats[0].notes[0]
    print(f"bend points: {[(p.position, p.value) for p in first_note.effect.bend.points]}")


if __name__ == "__main__":
    main()
