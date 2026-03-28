"""tests for MIDI rendering."""

from __future__ import annotations

from pathlib import Path

import pytest
from mido import MidiFile


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml"


class TestMidiRenderer:
    def test_render_score_writes_type1_midi_with_meta_and_part_tracks(self, tmp_path: Path) -> None:
        from pipeline.render.midi_renderer import MidiRenderer

        output_path = tmp_path / "render_multipart.mid"

        result = MidiRenderer.render_score(FIXTURES_DIR / "render_multipart.xml", output_path)

        midi_file = MidiFile(output_path)

        assert output_path.exists()
        assert midi_file.type == 1
        assert len(midi_file.tracks) == 4
        assert result.tempo_events == 1
        assert result.techniques_rendered == 0
        assert result.channel_map == {
            "P1": "channel=1,program=29,role=guitar",
            "P2": "channel=2,program=33,role=bass",
            "P3": "channel=10,program=none,role=drums",
        }

    def test_render_score_counts_rendered_techniques(self, tmp_path: Path) -> None:
        from pipeline.render.midi_renderer import MidiRenderer

        output_path = tmp_path / "render_techniques.mid"

        result = MidiRenderer.render_score(FIXTURES_DIR / "render_techniques.xml", output_path)

        assert output_path.exists()
        assert result.techniques_rendered == 5

    def test_render_score_raises_validation_error_for_missing_input(self, tmp_path: Path) -> None:
        from pipeline.render.errors import RenderValidationError
        from pipeline.render.midi_renderer import MidiRenderer

        with pytest.raises(RenderValidationError, match="MusicXML input not found"):
            MidiRenderer.render_score(tmp_path / "missing.xml", tmp_path / "out.mid")

    def test_render_score_chord_notes_play_simultaneously(self, tmp_path: Path) -> None:
        from pipeline.render.midi_renderer import MidiRenderer

        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Guitar</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><chord/><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>"""
        xml_path = tmp_path / "chord_test.xml"
        xml_path.write_bytes(xml_content)
        output_path = tmp_path / "chord_test.mid"

        MidiRenderer.render_score(xml_path, output_path)

        midi = MidiFile(output_path)
        part_track = midi.tracks[1]
        abs_tick = 0
        note_ons: list[tuple[int, int]] = []
        for msg in part_track:
            abs_tick += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                note_ons.append((msg.note, abs_tick))

        c_tick = next(t for n, t in note_ons if n == 60)
        e_tick = next(t for n, t in note_ons if n == 64)
        g_tick = next(t for n, t in note_ons if n == 67)
        d_tick = next(t for n, t in note_ons if n == 62)

        assert c_tick == e_tick == g_tick, "Chord notes must start at the same absolute tick"
        assert d_tick > c_tick, "Non-chord note D4 must start after the chord group"

    def test_render_score_expands_barline_repeats_before_midi(self, tmp_path: Path) -> None:
        from pipeline.render.midi_renderer import MidiRenderer

        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Guitar</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <barline location="left"><repeat direction="forward"/></barline>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
    <measure number="2">
      <barline location="right"><repeat direction="backward"/></barline>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
    <measure number="3">
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>"""
        xml_path = tmp_path / "repeat_test.xml"
        xml_path.write_bytes(xml_content)
        output_path = tmp_path / "repeat_test.mid"

        MidiRenderer.render_score(xml_path, output_path)

        midi = MidiFile(output_path)
        part_track = midi.tracks[1]
        note_ons = [msg for msg in part_track if msg.type == "note_on" and msg.velocity > 0]

        # Sequence should be: C, D, C, D, E (repeat section played twice)
        assert [msg.note for msg in note_ons] == [60, 62, 60, 62, 64]
