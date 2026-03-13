"""tests for Render tempo resolution."""

from __future__ import annotations

from mido import bpm2tempo


class TestTempoResolver:
    def test_build_meta_track_uses_explicit_tempo_and_metadata(self) -> None:
        from pipeline.render.tempo_resolver import TempoResolver

        fixture_path = (
            __import__("pathlib").Path(__file__).resolve().parents[2]
            / "fixtures"
            / "musicxml"
            / "render_multipart.xml"
        )

        result = TempoResolver.build_meta_track(fixture_path)

        assert result.tempo_events == 1
        assert result.warnings == []
        assert any(message.type == "set_tempo" and message.tempo == bpm2tempo(90) for message in result.track)
        assert any(
            message.type == "time_signature" and message.numerator == 4 and message.denominator == 4
            for message in result.track
        )
        assert any(message.type == "key_signature" for message in result.track)

    def test_build_meta_track_falls_back_to_default_tempo(self) -> None:
        from pathlib import Path

        from pipeline.render.tempo_resolver import TempoResolver

        fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml" / "render_techniques.xml"

        result = TempoResolver.build_meta_track(fixture_path)

        assert result.tempo_events == 1
        assert any(message.type == "set_tempo" and message.tempo == bpm2tempo(120) for message in result.track)
        assert any("120 BPM" in warning for warning in result.warnings)

    def test_build_meta_track_uses_overridden_default_tempo(self) -> None:
        from pathlib import Path

        from pipeline.render.tempo_resolver import TempoResolver

        fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml" / "render_techniques.xml"

        result = TempoResolver.build_meta_track(fixture_path, default_bpm=140)

        assert any(message.type == "set_tempo" and message.tempo == bpm2tempo(140) for message in result.track)
        assert any("140 BPM" in warning for warning in result.warnings)

    def test_build_meta_track_reads_multiple_tempo_events_from_fixture(self) -> None:
        from pathlib import Path

        from pipeline.render.tempo_resolver import TempoResolver

        fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml" / "render_tempo_changes.xml"

        result = TempoResolver.build_meta_track(fixture_path)

        tempo_messages = [message for message in result.track if message.type == "set_tempo"]

        assert result.tempo_events == 2
        assert len(tempo_messages) == 2
        assert any(message.tempo == bpm2tempo(90) for message in tempo_messages)
        assert any(message.tempo == bpm2tempo(120) for message in tempo_messages)
        assert any(message.type == "time_signature" and message.numerator == 3 and message.denominator == 4 for message in result.track)
        assert any(message.type == "key_signature" and message.key == "D" for message in result.track)