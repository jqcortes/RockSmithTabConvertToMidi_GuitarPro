"""tests for shared MusicXML fixture files."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml"


def _parse_fixture(name: str) -> etree._ElementTree:
    fixture_path = FIXTURE_DIR / name
    return etree.parse(str(fixture_path))


class TestMusicXmlFixtures:
    @pytest.mark.parametrize(
        ("name", "root_name"),
        [
            ("simple_guitar_tab.xml", "score-partwise"),
            ("no_tab.xml", "score-partwise"),
            ("multipart.xml", "score-partwise"),
            ("with_confidence.xml", "score-partwise"),
            ("transform_missing_part_info.xml", "score-partwise"),
            ("transform_measure_inconsistent.xml", "score-partwise"),
            ("transform_pitch_conflict.xml", "score-partwise"),
            ("transform_clean_tab.xml", "score-partwise"),
        ],
    )
    def test_required_valid_fixtures_exist_and_are_parseable(
        self,
        name: str,
        root_name: str,
    ) -> None:
        fixture_path = FIXTURE_DIR / name

        assert fixture_path.exists()
        tree = _parse_fixture(name)
        assert tree.getroot().tag == root_name

    def test_invalid_fixture_exists_and_is_not_well_formed(self) -> None:
        fixture_path = FIXTURE_DIR / "invalid.xml"

        assert fixture_path.exists()
        with pytest.raises(etree.XMLSyntaxError):
            etree.parse(str(fixture_path))

    def test_simple_guitar_tab_fixture_contains_tab_staff_and_technical_data(self) -> None:
        tree = _parse_fixture("simple_guitar_tab.xml")

        tab_clef_count = tree.xpath(
            "count(//*[local-name()='clef'][*[local-name()='sign']='TAB'])"
        )
        fret_count = tree.xpath(
            "count(//*[local-name()='technical']/*[local-name()='fret'])"
        )
        string_count = tree.xpath(
            "count(//*[local-name()='technical']/*[local-name()='string'])"
        )

        assert tab_clef_count == 1.0
        assert fret_count >= 1.0
        assert string_count >= 1.0

    def test_no_tab_fixture_contains_no_tab_clef(self) -> None:
        tree = _parse_fixture("no_tab.xml")

        tab_clef_count = tree.xpath(
            "count(//*[local-name()='clef'][*[local-name()='sign']='TAB'])"
        )

        assert tab_clef_count == 0.0

    def test_multipart_fixture_contains_guitar_bass_and_drums_parts(self) -> None:
        tree = _parse_fixture("multipart.xml")

        part_names = tree.xpath(
            "//*[local-name()='score-part']/*[local-name()='part-name']/text()"
        )

        assert part_names == ["Lead Guitar", "Bass", "Drums"]

    def test_with_confidence_fixture_contains_below_threshold_note(self) -> None:
        tree = _parse_fixture("with_confidence.xml")

        low_confidence_count = tree.xpath("count(//*[local-name()='note'][@confidence='0.4'])")
        high_confidence_count = tree.xpath("count(//*[local-name()='note'][@confidence='0.9'])")

        assert low_confidence_count == 1.0
        assert high_confidence_count == 1.0

    def test_transform_quality_gate_fixtures_cover_missing_part_info_and_conflict_cases(self) -> None:
        missing_part_info = _parse_fixture("transform_missing_part_info.xml")
        measure_inconsistent = _parse_fixture("transform_measure_inconsistent.xml")
        pitch_conflict = _parse_fixture("transform_pitch_conflict.xml")
        clean_tab = _parse_fixture("transform_clean_tab.xml")

        assert missing_part_info.xpath("count(//*[local-name()='part-list'])") == 0.0
        assert measure_inconsistent.xpath("count(//*[local-name()='part'][@id='P1']/*[local-name()='measure'])") == 2.0
        assert measure_inconsistent.xpath("count(//*[local-name()='part'][@id='P2']/*[local-name()='measure'])") == 1.0
        assert pitch_conflict.xpath("count(//*[local-name()='technical']/*[local-name()='fret'])") == 1.0
        assert clean_tab.xpath("count(//*[local-name()='clef'][*[local-name()='sign']='TAB'])") == 1.0