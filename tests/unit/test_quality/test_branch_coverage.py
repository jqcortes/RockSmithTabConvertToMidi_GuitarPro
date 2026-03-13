"""branch coverage tests for Quality helpers."""

from __future__ import annotations

from lxml import etree


def _parse_tree(content: str) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(content.encode("utf-8")))


class TestQualityMetricsBranches:
    def test_calculate_handles_empty_score(self) -> None:
        from pipeline.quality.metrics import QualityMetricsCalculator

        tree = _parse_tree("<score-partwise version=\"4.0\"><part-list/></score-partwise>")

        result = QualityMetricsCalculator.calculate(tree, expected_parts=[])

        assert result.measure_completeness == 0.0
        assert result.pitch_range_validity == 0.0
        assert result.part_detection_rate == 0.0
        assert result.total_measures == 0
        assert result.total_notes == 0

    def test_helper_paths_cover_role_fallbacks_and_invalid_pitch(self) -> None:
        from pipeline.quality import metrics as quality_metrics

        tree = _parse_tree(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id=""><part-name></part-name></score-part>
  </part-list>
  <part id="">
    <measure number="1">
      <attributes><time><beats>x</beats><beat-type>y</beat-type></time></attributes>
      <note><rest/><duration>1</duration></note>
      <note><pitch><step>Z</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>
""".strip()
        )
        part = tree.xpath("//*[local-name()='part']")[0]
        measure = tree.xpath("//*[local-name()='measure']")[0]
        bad_note = tree.xpath("//*[local-name()='note'][2]")[0]

        assert quality_metrics._part_role(part, "Strings") == "other"
        assert quality_metrics._part_name(tree, "") == "Unknown"
        assert quality_metrics._measure_divisions(measure, 8) == 8
        assert quality_metrics._measure_time_signature(measure, (3, 4)) == (3, 4)
        assert quality_metrics._pitch_to_midi(bad_note) is None
        assert quality_metrics._note_in_range(40, "bass") is True
        assert quality_metrics._note_in_range(10, "drums") is True
        assert quality_metrics._is_float("not-a-number") is False

    def test_omr_confidence_uses_signal_fallback(self) -> None:
        from pipeline.quality import metrics as quality_metrics

        tree = _parse_tree(
            """
<score-partwise version="4.0">
  <part-list/>
  <part id="P1">
    <measure number="1">
      <direction><sound tempo="120"/></direction>
      <direction><direction-type><metronome><per-minute>120</per-minute></metronome></direction-type></direction>
    </measure>
  </part>
</score-partwise>
""".strip()
        )

        assert quality_metrics._omr_confidence(tree) == 0.85