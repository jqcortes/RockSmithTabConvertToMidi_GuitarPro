"""fixture availability tests for Quality."""

from __future__ import annotations

from pathlib import Path


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml"


class TestQualityFixtures:
    def test_quality_specific_fixtures_exist(self) -> None:
        expected = {
            "quality_good.xml",
            "quality_measure_incomplete.xml",
            "quality_out_of_range.xml",
        }

        assert expected.issubset({path.name for path in FIXTURES_DIR.iterdir()})

    def test_quality_good_fixture_contains_roles_and_confidence(self) -> None:
        content = (FIXTURES_DIR / "quality_good.xml").read_text(encoding="utf-8")

        assert 'transform:role="guitar"' in content
        assert 'transform:role="bass"' in content
        assert 'transform:role="drums"' in content
        assert 'confidence="0.8"' in content
        assert 'confidence="0.9"' in content
