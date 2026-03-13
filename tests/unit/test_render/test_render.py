"""tests for public render entrypoint."""

from __future__ import annotations

from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml"


class TestRenderEntrypoint:
    def test_render_returns_cached_step_result_when_output_exists(self, tmp_path: Path) -> None:
        from pipeline.render import render

        cached_output = tmp_path / "render_multipart.mid"
        cached_output.write_bytes(b"MThd")

        result = render(FIXTURES_DIR / "render_multipart.xml", tmp_path)

        assert result.success is True
        assert result.output_path == cached_output
        assert result.metrics["cached"] is True

    def test_render_writes_midi_and_aggregates_metrics(self, tmp_path: Path) -> None:
        from pipeline.render import render

        result = render(FIXTURES_DIR / "render_techniques.xml", tmp_path)

        assert result.success is True
        assert result.output_path == tmp_path / "render_techniques.mid"
        assert result.metrics["cached"] is False
        assert result.metrics["tempo_events"] == 1
        assert result.metrics["techniques_rendered"] == 5
        assert isinstance(result.metrics["channel_map"], dict)
        assert any("120 BPM" in warning for warning in result.warnings)

    def test_render_re_raises_validation_errors(self, tmp_path: Path) -> None:
        from pipeline.render import render
        from pipeline.render.errors import RenderValidationError

        with pytest.raises(RenderValidationError):
            render(tmp_path / "missing.xml", tmp_path)

    def test_render_wraps_unexpected_errors(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        from pipeline.render import render
        from pipeline.render.errors import RenderExecutionError

        def raise_runtime_error(*_args: object, **_kwargs: object) -> object:
            raise RuntimeError("boom")

        monkeypatch.setattr("pipeline.render._render.MidiRenderer.render_score", raise_runtime_error)

        with pytest.raises(RenderExecutionError, match="boom"):
            render(FIXTURES_DIR / "render_multipart.xml", tmp_path)

    def test_render_passes_default_tempo_and_pitch_bend_range(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        from pipeline.render import render

        captured: dict[str, object] = {}

        def fake_render_score(
            musicxml_path: Path,
            output_path: Path,
            *,
            default_bpm: int = 120,
            pitch_bend_range: int = 2,
        ) -> object:
            captured["musicxml_path"] = musicxml_path
            captured["output_path"] = output_path
            captured["default_bpm"] = default_bpm
            captured["pitch_bend_range"] = pitch_bend_range

            class _Result:
                def __init__(self) -> None:
                    self.output_path = output_path
                    self.channel_map = {}
                    self.tempo_events = 1
                    self.techniques_rendered = 0
                    self.warnings = []

            output_path.write_bytes(b"MThd")
            return _Result()

        monkeypatch.setattr("pipeline.render._render.MidiRenderer.render_score", fake_render_score)

        result = render(FIXTURES_DIR / "render_multipart.xml", tmp_path, default_bpm=140, pitch_bend_range=4)

        assert result.success is True
        assert captured["default_bpm"] == 140
        assert captured["pitch_bend_range"] == 4