"""tests for Render technique handling."""

from __future__ import annotations

from lxml import etree
from mido import MidiTrack


def _parse_note(content: str) -> etree._Element:
    return etree.fromstring(content.encode("utf-8"))


class TestTechniqueRenderer:
    def test_render_note_techniques_adds_pitchwheel_and_expression_messages(self) -> None:
        from pipeline.render.technique_renderer import TechniqueRenderer

        note = _parse_note(
            """
<note>
  <pitch><step>E</step><octave>4</octave></pitch>
  <duration>2</duration>
  <notations>
    <technical>
      <bend><bend-alter>1</bend-alter></bend>
      <slide number="1" type="start" line-type="solid"/>
      <palm-mute>P.M.</palm-mute>
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
            velocity=80,
        )

        assert result.technique_count == 3
        assert result.duration_ticks == 240
        assert any(message.type == "pitchwheel" and message.pitch != 0 for message in track)
        assert any(message.type == "control_change" and message.control == 11 and message.value == 40 for message in track)
        assert any(message.type == "control_change" and message.control == 11 and message.value == 127 for message in track)

    def test_render_note_techniques_reduces_velocity_for_hammer_on_and_pull_off(self) -> None:
        from pipeline.render.technique_renderer import TechniqueRenderer

        note = _parse_note(
            """
<note>
  <pitch><step>F</step><octave>4</octave></pitch>
  <duration>2</duration>
  <notations>
    <technical>
      <hammer-on number="1" type="start">H</hammer-on>
      <pull-off number="1" type="start">P</pull-off>
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
            base_note=65,
            duration_ticks=480,
            velocity=100,
        )

        assert result.technique_count == 2
        assert result.velocity == 42

    def test_render_note_techniques_uses_custom_pitch_bend_range(self) -> None:
        from pipeline.render.technique_renderer import TechniqueRenderer

        note = _parse_note(
            """
<note>
  <pitch><step>E</step><octave>4</octave></pitch>
  <duration>2</duration>
  <notations>
    <technical>
      <bend><bend-alter>1</bend-alter></bend>
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
            velocity=80,
            pitch_bend_range=4,
        )

        assert result.technique_count == 1
        pitchwheel_values = [message.pitch for message in track if message.type == "pitchwheel" and message.pitch != 0]
        assert pitchwheel_values == [2047]