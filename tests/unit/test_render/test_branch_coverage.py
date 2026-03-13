"""branch coverage tests for Render helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree
from mido import MidiTrack, bpm2tempo

from pipeline.render.errors import RenderValidationError


def _parse_element(content: str) -> etree._Element:
    return etree.fromstring(content.encode("utf-8"))


class TestTempoResolverBranches:
    def test_build_meta_track_raises_for_invalid_xml(self, tmp_path: Path) -> None:
        from pipeline.render.tempo_resolver import TempoResolver

        invalid_xml = tmp_path / "invalid.xml"
        invalid_xml.write_text("<score-partwise>", encoding="utf-8")

        with pytest.raises(RenderValidationError, match="Failed to parse MusicXML"):
            TempoResolver.build_meta_track(invalid_xml)

    def test_build_meta_track_defaults_time_signature_and_key(self, tmp_path: Path) -> None:
        from pipeline.render.tempo_resolver import TempoResolver

        xml_path = tmp_path / "minimal.xml"
        xml_path.write_text(
            "<score-partwise version=\"4.0\"><part-list/><part id=\"P1\"><measure number=\"1\"/></part></score-partwise>",
            encoding="utf-8",
        )

        result = TempoResolver.build_meta_track(xml_path)

        assert any(message.type == "set_tempo" and message.tempo == bpm2tempo(120) for message in result.track)
        assert any(
            message.type == "time_signature" and message.numerator == 4 and message.denominator == 4
            for message in result.track
        )
        assert any(message.type == "key_signature" and message.key == "C" for message in result.track)


class TestTechniqueRendererBranches:
    def test_render_note_techniques_ignores_missing_and_invalid_technique_values(self) -> None:
        from pipeline.render.technique_renderer import TechniqueRenderer

        note = _parse_element(
            """
<note>
  <pitch><step>E</step><octave>4</octave></pitch>
  <notations>
    <technical>
      <bend><bend-alter>bad</bend-alter></bend>
    </technical>
  </notations>
</note>
""".strip()
        )
        track = MidiTrack()

        result = TechniqueRenderer.render_note_techniques(
            note,
            track,
            midi_channel=1,
            base_note=64,
            duration_ticks=480,
            velocity=90,
        )

        assert result.technique_count == 0
        assert result.velocity == 90
        assert list(track) == []


class TestMidiRendererBranches:
    def test_render_score_raises_for_invalid_xml(self, tmp_path: Path) -> None:
        from pipeline.render.midi_renderer import MidiRenderer

        invalid_xml = tmp_path / "invalid.xml"
        invalid_xml.write_text("<score-partwise>", encoding="utf-8")

        with pytest.raises(RenderValidationError, match="Failed to parse MusicXML"):
            MidiRenderer.render_score(invalid_xml, tmp_path / "out.mid")

    def test_render_score_skips_parts_without_id(self, tmp_path: Path) -> None:
        from mido import MidiFile

        from pipeline.render.midi_renderer import MidiRenderer

        xml_path = tmp_path / "no_id.xml"
        xml_path.write_text(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Lead Guitar</part-name></score-part>
  </part-list>
  <part><measure number="1"><note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note></measure></part>
</score-partwise>
""".strip(),
            encoding="utf-8",
        )

        output_path = tmp_path / "no_id.mid"
        MidiRenderer.render_score(xml_path, output_path)

        midi_file = MidiFile(output_path)
        assert len(midi_file.tracks) == 1

    def test_render_score_handles_missing_assignment(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        from mido import MidiFile

        from pipeline.render.midi_renderer import MidiRenderer

        fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml" / "render_multipart.xml"
        output_path = tmp_path / "missing_assignment.mid"

        monkeypatch.setattr("pipeline.render.midi_renderer.ChannelMapper.assign", lambda _parts: [])

        MidiRenderer.render_score(fixture_path, output_path)

        midi_file = MidiFile(output_path)
        assert len(midi_file.tracks) == 1

    def test_helper_methods_cover_inference_and_defaults(self) -> None:
        from pipeline.render.midi_renderer import MidiRenderer

        part = _parse_element("<part id=\"P1\" />")
        percussion_part = _parse_element("<part id=\"P2\" />")
        measure = _parse_element("<measure number=\"1\" />")
        note_without_duration = _parse_element("<note><pitch><step>Z</step><octave>4</octave></pitch></note>")

        assert MidiRenderer._part_role(part, "Strings") == "other"
        assert MidiRenderer._part_role(percussion_part, "Percussion") == "drums"
        assert MidiRenderer._measure_divisions(measure, 8) == 8
        assert MidiRenderer._duration_value(note_without_duration) == 1
        assert MidiRenderer._pitch_to_midi(note_without_duration) is None
        assert MidiRenderer._string_value(None) == ""