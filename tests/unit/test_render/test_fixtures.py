"""fixture availability tests for Render."""

from __future__ import annotations

from pathlib import Path


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml"


class TestRenderFixtures:
    def test_render_specific_fixtures_exist(self) -> None:
        expected = {
            "render_multipart.xml",
            "render_techniques.xml",
            "render_tempo_changes.xml",
        }

        assert expected.issubset({path.name for path in FIXTURES_DIR.iterdir()})

    def test_render_multipart_fixture_contains_three_roles(self) -> None:
        content = (FIXTURES_DIR / "render_multipart.xml").read_text(encoding="utf-8")

        assert 'transform:role="guitar"' in content
        assert 'transform:role="bass"' in content
        assert 'transform:role="drums"' in content

    def test_render_techniques_fixture_contains_required_techniques(self) -> None:
        content = (FIXTURES_DIR / "render_techniques.xml").read_text(encoding="utf-8")

        assert "<bend>" in content
        assert "<slide" in content
        assert "<palm-mute>" in content
        assert "<hammer-on" in content
        assert "<pull-off" in content

    def test_render_tempo_changes_fixture_contains_multiple_tempos_and_three_four_time(self) -> None:
        content = (FIXTURES_DIR / "render_tempo_changes.xml").read_text(encoding="utf-8")

        assert 'tempo="90"' in content
        assert 'tempo="120"' in content
        assert "<beats>3</beats>" in content
        assert "<beat-type>4</beat-type>" in content