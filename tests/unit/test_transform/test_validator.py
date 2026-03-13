"""tests for MusicXmlValidator xml validation."""

from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from pipeline.transform.errors import TransformValidationError


def _write_text(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _write_mxl(path: Path, xml_name: str, content: str) -> Path:
  with zipfile.ZipFile(path, "w") as archive:
    archive.writestr(xml_name, content)
  return path


class TestMusicXmlValidatorXml:
    """Task 2.1 RED tests for plain xml validation."""

    def test_validate_returns_counts_for_valid_score_partwise_xml(
        self,
        tmp_path: Path,
    ) -> None:
        from pipeline.transform.validator import MusicXmlValidator

        xml_path = _write_text(
            tmp_path / "valid.xml",
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1">
      <part-name>Guitar</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <staves>2</staves>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>quarter</type>
        <staff>1</staff>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>quarter</type>
        <staff>2</staff>
      </note>
    </measure>
  </part>
</score-partwise>
""".strip(),
        )

        result = MusicXmlValidator.validate(xml_path)

        assert result.part_count == 1
        assert result.measure_count == 1
        assert result.staff_count == 2
        assert result.tree.getroot().tag == "score-partwise"

    def test_validate_raises_for_missing_file(self, tmp_path: Path) -> None:
        from pipeline.transform.validator import MusicXmlValidator

        xml_path = tmp_path / "missing.xml"

        with pytest.raises(TransformValidationError, match="見つかりません|存在"):
            MusicXmlValidator.validate(xml_path)

    def test_validate_raises_for_invalid_xml(self, tmp_path: Path) -> None:
        from pipeline.transform.validator import MusicXmlValidator

        xml_path = _write_text(
            tmp_path / "invalid.xml",
            "<score-partwise><part></score-partwise>",
        )

        with pytest.raises(TransformValidationError, match="well-formed"):
            MusicXmlValidator.validate(xml_path)

    def test_validate_raises_for_invalid_root_element(self, tmp_path: Path) -> None:
        from pipeline.transform.validator import MusicXmlValidator

        xml_path = _write_text(
            tmp_path / "wrong_root.xml",
            "<foo><part id=\"P1\" /></foo>",
        )

        with pytest.raises(TransformValidationError, match="ルート要素|root"):
            MusicXmlValidator.validate(xml_path)


class TestMusicXmlValidatorMxl:
    """Task 2.2/2.3 RED tests for `.mxl` validation."""

    def test_validate_returns_counts_for_valid_mxl(self, tmp_path: Path) -> None:
        from pipeline.transform.validator import MusicXmlValidator

        mxl_path = _write_mxl(
            tmp_path / "valid.mxl",
            "score.xml",
            """
<score-timewise version="4.0">
  <part-list>
    <score-part id="P1">
      <part-name>Bass</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <staves>1</staves>
      </attributes>
      <note>
        <pitch><step>F</step><octave>2</octave></pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>quarter</type>
        <staff>1</staff>
      </note>
    </measure>
  </part>
</score-timewise>
""".strip(),
        )

        result = MusicXmlValidator.validate(mxl_path)

        assert result.part_count == 1
        assert result.measure_count == 1
        assert result.staff_count == 1
        assert result.tree.getroot().tag == "score-timewise"

    def test_validate_raises_for_invalid_mxl_zip(self, tmp_path: Path) -> None:
        from pipeline.transform.validator import MusicXmlValidator

        mxl_path = _write_text(tmp_path / "invalid.mxl", "not a zip archive")

        with pytest.raises(TransformValidationError, match="ZIP|mxl"):
            MusicXmlValidator.validate(mxl_path)