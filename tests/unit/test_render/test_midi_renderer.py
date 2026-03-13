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