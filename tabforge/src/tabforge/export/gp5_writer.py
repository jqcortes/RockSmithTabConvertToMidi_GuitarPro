"""GP5 エクスポート（設計書 §10.1、実装指示書 T9 / T0-3）。

⚠検証済み API（`scripts/probe_pyguitarpro.py` で実測。PyGuitarPro 0.11 系）:

- ``GuitarString(number, value)``: ``number=1`` が 1弦（最高音）。
  IR の ``tuning[0]``（最高音弦）を ``string=1`` に単純写像する。
  ここを逆にすると全譜面が上下反転する（設計書 §10.1 の警告どおり）。
- ``Note(beat, value=fret, string=string_number, type=NoteType.normal|tie|dead)``。
  ``velocity`` は MuScriptor に存在しないためデフォルト値のまま使わない。
- ``Duration(value={1,2,4,8,16,32,64}, isDotted=bool, tuplet=Tuplet(enters, times))``。
  tuplet 無しは ``Tuplet()``（既定 enters=1, times=1）。
- ``NoteEffect.bend = BendEffect(type=BendType.bend, points=[BendPoint(position=0-12, value=1半音=4), ...])``。
- ``MeasureHeader.start`` / ``Beat.start`` は ``gp.write()`` 時に自動再計算される
  （手動で設定しても保存時に上書きされる。960 = 四分音符1拍分のtick）。
- 空の休符 Beat を複数連続で入れると、再パース後に統合されることを実測で確認した。
  そのため本実装では 1小節を「実音符 Beat 群 + 末尾の休符 Beat 最大1つ」に
  正規化してから書き出す（設計書 #9: 空小節にも必ず休符 Beat を入れる、に対応）。
"""
from __future__ import annotations

from pathlib import Path

import guitarpro as gp

from tabforge.ir.models import GpDuration, TabIR, TabNote, TabTrack

_NOTE_TYPE = {"normal": gp.NoteType.normal, "tie": gp.NoteType.tie, "dead": gp.NoteType.dead}


def _gp_duration(duration: GpDuration) -> gp.Duration:
    tuplet = gp.Tuplet(enters=duration.tuplet[0], times=duration.tuplet[1]) if duration.tuplet else gp.Tuplet()
    return gp.Duration(value=duration.value, isDotted=duration.dotted, tuplet=tuplet)


def _build_note(beat: gp.Beat, note_ir: TabNote) -> gp.Note:
    note = gp.Note(beat, value=note_ir.fret, string=note_ir.string, type=_NOTE_TYPE[note_ir.type])
    eff = note_ir.effects
    if eff.bend is not None:
        note.effect.bend = gp.BendEffect(
            type=gp.BendType.bend,
            points=[gp.BendPoint(position=p, value=v) for p, v in eff.bend.points],
        )
    note.effect.vibrato = eff.vibrato
    note.effect.hammer = eff.hammer
    note.effect.palmMute = eff.palm_mute
    note.effect.letRing = eff.let_ring
    if eff.slide:
        note.effect.slides = [getattr(gp.SlideType, eff.slide)]
    return note


def _build_beat(voice: gp.Voice, beat_ir) -> gp.Beat:
    beat = gp.Beat(voice)
    beat.duration = _gp_duration(beat_ir.duration)
    if not beat_ir.notes:
        beat.status = gp.BeatStatus.rest
        beat.notes = []
    else:
        beat.notes = [_build_note(beat, n) for n in beat_ir.notes]
    return beat


def _build_track(song: gp.Song, track_ir: TabTrack, headers: list[gp.MeasureHeader]) -> gp.Track:
    track = gp.Track(song, name=track_ir.name[:40])
    # index 0 = 最高音弦 → GP の string=1 に単純写像する（設計書 §10.1）。
    track.strings = [gp.GuitarString(i + 1, pitch) for i, pitch in enumerate(track_ir.tuning)]
    track.measures = []
    for header, measure_ir in zip(headers, track_ir.measures, strict=True):
        measure = gp.Measure(track, header)
        voice = measure.voices[0]
        voice.beats = [_build_beat(voice, b) for b in measure_ir.beats] or [
            _rest_beat(voice, measure_ir.time_signature)
        ]
        measure.voices[0] = voice
        track.measures.append(measure)
    return track


def _rest_beat(voice: gp.Voice, time_signature: tuple[int, int]) -> gp.Beat:
    _numerator, denominator = time_signature
    beat = gp.Beat(voice)
    beat.duration = gp.Duration(value=denominator)
    beat.status = gp.BeatStatus.rest
    beat.notes = []
    return beat


def write_gp5(tab: TabIR, out: Path, tempo: int = 120, title: str = "TabForge") -> None:
    if not tab.tracks:
        raise ValueError("tab.tracks が空のため GP5 を書き出せない")

    song = gp.Song(title=title, tempo=tempo)
    song.tracks = []

    reference_measures = tab.tracks[0].measures
    headers: list[gp.MeasureHeader] = []
    for measure_ir in reference_measures:
        header = gp.MeasureHeader(number=measure_ir.bar)
        numerator, denominator = measure_ir.time_signature
        header.timeSignature = gp.TimeSignature(numerator=numerator, denominator=gp.Duration(value=denominator))
        headers.append(header)
    song.measureHeaders = headers

    for track_ir in tab.tracks:
        song.tracks.append(_build_track(song, track_ir, headers))

    out.parent.mkdir(parents=True, exist_ok=True)
    gp.write(song, str(out), version=(5, 1, 0))
