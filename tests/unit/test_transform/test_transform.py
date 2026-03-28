"""tests for transform() entrypoint and cache behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from lxml import etree

from pipeline.transform.confidence_filter import FilterResult, RemovedNote
from pipeline.transform.errors import TransformError, TransformValidationError
from pipeline.transform.guitar_fixer import FixerResult
from pipeline.transform.part_identifier import PartIdentifierResult, PartInfo
from pipeline.transform.validator import ValidationResult


def _parse_tree(content: str) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(content.encode("utf-8")))


def _write_input_xml(path: Path) -> Path:
    path.write_text(
        (
            "<score-partwise version=\"4.0\">"
            "<part-list><score-part id=\"P1\"><part-name>Lead Guitar</part-name></score-part></part-list>"
            "<part id=\"P1\"><measure number=\"1\" /></part>"
            "</score-partwise>"
        ),
        encoding="utf-8",
    )
    return path


class TestTransformCacheHit:
    def test_transform_returns_cached_step_result_when_output_exists(
        self,
        tmp_path: Path,
    ) -> None:
        from pipeline.transform._transform import transform

        musicxml_path = _write_input_xml(tmp_path / "score.xml")
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        cached_output = output_dir / "score_transformed.xml"
        cached_output.write_text("<score-partwise />", encoding="utf-8")

        with patch(
            "pipeline.transform._transform.MusicXmlValidator.validate"
        ) as validate_mock:
            result = transform(musicxml_path, output_dir)

        validate_mock.assert_not_called()
        assert result.success is True
        assert result.output_path == cached_output
        assert result.metrics["cached"] is True
        assert result.metrics["elapsed_seconds"] == 0.0
        assert result.metrics["musicxml_path"] == str(cached_output)


class TestTransformCacheMiss:
    def test_transform_runs_fallback_pipeline_when_quality_gate_requires_it(
        self,
        tmp_path: Path,
    ) -> None:
        from pipeline.transform._transform import transform
        from pipeline.transform.tab_ocr import TabOcrResult, TabOcrToken

        musicxml_path = _write_input_xml(tmp_path / "score.xml")
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        image_path = tmp_path / "page.png"
        image_path.write_bytes(b"png")
        tree = _parse_tree(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Lead Guitar</part-name></score-part>
  </part-list>
  <part id="P1" xmlns:transform="https://band-score-to-midi/transform">
    <measure number="1">
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>1</duration>
      </note>
    </measure>
  </part>
</score-partwise>
""".strip()
        )
        validation_result = ValidationResult(
            tree=tree,
            part_count=1,
            measure_count=1,
            staff_count=2,
        )
        fixer_result = FixerResult(tree=tree, applied=2, skipped=1)
        part_result = PartIdentifierResult(
            parts=[
                PartInfo(
                    part_id="P1",
                    part_name="Lead Guitar",
                    role="guitar",
                    tab_staff_id="2",
                )
            ],
            parts_map={"P1": "guitar"},
            warnings=["Unknown Pad"],
        )
        filter_result = FilterResult(
            tree=tree,
            removed=[
                RemovedNote(
                    measure="1",
                    part_id="P1",
                    pitch="C4",
                    confidence=0.4,
                )
            ],
            total=4,
        )

        with patch(
            "pipeline.transform._transform.MusicXmlValidator.validate",
            return_value=validation_result,
        ) as validate_mock:
            with patch(
                "pipeline.transform._transform._evaluate_quality_gate",
                return_value=(True, ["tab_staff_missing"]),
            ) as gate_mock:
                with patch(
                    "pipeline.transform._transform.TabOcrScanner.extract_tokens",
                    return_value=TabOcrResult(
                        tokens=[
                            TabOcrToken(
                                staff_group=0,
                                string=1,
                                fret=3,
                                x=100,
                                y=30,
                                confidence=95.0,
                            )
                        ],
                        warnings=[],
                        tesseract_path=tmp_path / "tesseract.exe",
                    ),
                ) as ocr_mock:
                    with patch(
                        "pipeline.transform._transform.GuitarFixer.apply",
                        return_value=fixer_result,
                    ) as fixer_mock:
                        with patch(
                            "pipeline.transform._transform.PartIdentifier.identify",
                            return_value=part_result,
                        ) as identify_mock:
                            with patch(
                                "pipeline.transform._transform.PartIdentifier.annotate",
                                return_value=tree,
                            ) as annotate_mock:
                                with patch(
                                    "pipeline.transform._transform.ConfidenceFilter.filter",
                                    return_value=filter_result,
                                ) as filter_mock:
                                    result = transform(
                                        musicxml_path,
                                        output_dir,
                                        preprocessed_image_path=image_path,
                                    )

        output_path = output_dir / "score_transformed.xml"
        assert output_path.exists()
        assert "score-partwise" in output_path.read_text(encoding="utf-8")
        validate_mock.assert_called_once_with(musicxml_path)
        gate_mock.assert_called_once_with(validation_result)
        ocr_mock.assert_called_once_with(image_path, tesseract_path=None)
        fixer_mock.assert_called_once_with(tree, tuning=None, ocr_tokens=ocr_mock.return_value.tokens)
        identify_mock.assert_called_once()
        annotate_mock.assert_called_once()
        filter_mock.assert_called_once()

        assert result.success is True
        assert result.output_path == output_path
        assert result.metrics["cached"] is False
        assert result.metrics["musicxml_path"] == str(output_path)
        assert result.metrics["fallback_required"] is True
        assert result.metrics["fallback_reasons"] == ["tab_staff_missing"]
        assert result.metrics["part_count"] == 1
        assert result.metrics["measure_count"] == 1
        assert result.metrics["staff_count"] == 2
        assert result.metrics["fixer_applied"] == 2
        assert result.metrics["fixer_skipped"] == 1
        assert result.metrics["tab_ocr_tokens"] == 1
        assert result.metrics["tab_ocr_applied"] == 0
        assert result.metrics["tab_ocr_skipped"] == 0
        assert result.metrics["filtered_notes"] == 1
        assert result.metrics["filter_rate"] == 0.25
        assert result.metrics["identified_parts"] == 1
        assert result.metrics["parts"] == {"P1": "guitar"}
        assert result.warnings == ["Unknown Pad", "Filtered note: part=P1 measure=1 pitch=C4 confidence=0.4"]

    def test_transform_skips_rescue_steps_when_quality_gate_passes(
        self,
        tmp_path: Path,
    ) -> None:
        from pipeline.transform._transform import transform

        musicxml_path = _write_input_xml(tmp_path / "score.xml")
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        tree = _parse_tree(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Lead Guitar</part-name></score-part>
  </part-list>
  <part id="P1"><measure number="1" /></part>
</score-partwise>
""".strip()
        )
        validation_result = ValidationResult(
            tree=tree,
            part_count=1,
            measure_count=1,
            staff_count=1,
        )
        part_result = PartIdentifierResult(
            parts=[
                PartInfo(
                    part_id="P1",
                    part_name="Lead Guitar",
                    role="guitar",
                    tab_staff_id=None,
                )
            ],
            parts_map={"P1": "guitar"},
            warnings=[],
        )

        with patch(
            "pipeline.transform._transform.MusicXmlValidator.validate",
            return_value=validation_result,
        ) as validate_mock:
            with patch(
                "pipeline.transform._transform._evaluate_quality_gate",
                return_value=(False, []),
            ) as gate_mock:
                with patch(
                    "pipeline.transform._transform.GuitarFixer.apply"
                ) as fixer_mock:
                    with patch(
                        "pipeline.transform._transform.PartIdentifier.identify",
                        return_value=part_result,
                    ) as identify_mock:
                        with patch(
                            "pipeline.transform._transform.PartIdentifier.annotate",
                            return_value=tree,
                        ) as annotate_mock:
                            with patch(
                                "pipeline.transform._transform.ConfidenceFilter.filter"
                            ) as filter_mock:
                                result = transform(musicxml_path, output_dir)

        validate_mock.assert_called_once_with(musicxml_path)
        gate_mock.assert_called_once_with(validation_result)
        fixer_mock.assert_not_called()
        filter_mock.assert_not_called()
        identify_mock.assert_called_once()
        annotate_mock.assert_called_once()
        assert result.metrics["fallback_required"] is False
        assert result.metrics["fallback_reasons"] == []
        assert result.metrics["fixer_applied"] == 0
        assert result.metrics["fixer_skipped"] == 0
        assert result.metrics["tab_ocr_tokens"] == 0
        assert result.metrics["tab_ocr_applied"] == 0
        assert result.metrics["tab_ocr_skipped"] == 0
        assert result.metrics["filtered_notes"] == 0
        assert result.metrics["filter_rate"] == 0.0
        assert result.metrics["parts"] == {"P1": "guitar"}

    def test_transform_includes_tab_ocr_warning_when_tesseract_is_unavailable(
        self,
        tmp_path: Path,
    ) -> None:
        from pipeline.transform._transform import transform
        from pipeline.transform.tab_ocr import TabOcrResult

        musicxml_path = _write_input_xml(tmp_path / "score.xml")
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        image_path = tmp_path / "page.png"
        image_path.write_bytes(b"png")
        tree = _parse_tree(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Lead Guitar</part-name></score-part>
  </part-list>
  <part id="P1"><measure number="1" /></part>
</score-partwise>
""".strip()
        )
        validation_result = ValidationResult(
            tree=tree,
            part_count=1,
            measure_count=1,
            staff_count=1,
        )
        part_result = PartIdentifierResult(
            parts=[PartInfo(part_id="P1", part_name="Lead Guitar", role="guitar", tab_staff_id=None)],
            parts_map={"P1": "guitar"},
            warnings=[],
        )

        with patch(
            "pipeline.transform._transform.MusicXmlValidator.validate",
            return_value=validation_result,
        ):
            with patch(
                "pipeline.transform._transform._evaluate_quality_gate",
                return_value=(True, ["pitch_tab_conflict"]),
            ):
                with patch(
                    "pipeline.transform._transform.TabOcrScanner.extract_tokens",
                    return_value=TabOcrResult(
                        tokens=[],
                        warnings=["TAB OCR skipped: tesseract executable not found"],
                        tesseract_path=None,
                    ),
                ):
                    with patch(
                        "pipeline.transform._transform.GuitarFixer.apply",
                        return_value=FixerResult(tree=tree, applied=0, skipped=0),
                    ):
                        with patch(
                            "pipeline.transform._transform.PartIdentifier.identify",
                            return_value=part_result,
                        ):
                            with patch(
                                "pipeline.transform._transform.PartIdentifier.annotate",
                                return_value=tree,
                            ):
                                with patch(
                                    "pipeline.transform._transform.ConfidenceFilter.filter",
                                    return_value=FilterResult(tree=tree, removed=[], total=0),
                                ):
                                    result = transform(
                                        musicxml_path,
                                        output_dir,
                                        preprocessed_image_path=image_path,
                                    )

        assert "TAB OCR skipped: tesseract executable not found" in result.warnings

    def test_transform_propagates_transform_errors(self, tmp_path: Path) -> None:
        from pipeline.transform._transform import transform

        musicxml_path = _write_input_xml(tmp_path / "broken.xml")
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        with patch(
            "pipeline.transform._transform.MusicXmlValidator.validate",
            side_effect=TransformValidationError("invalid xml"),
        ):
            with pytest.raises(TransformValidationError, match="invalid xml"):
                transform(musicxml_path, output_dir)

    def test_transform_wraps_unexpected_errors(self, tmp_path: Path) -> None:
        from pipeline.transform._transform import transform

        musicxml_path = _write_input_xml(tmp_path / "broken.xml")
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        tree = _parse_tree("<score-partwise version=\"4.0\"><part-list /><part id=\"P1\" /></score-partwise>")
        validation_result = ValidationResult(
            tree=tree,
            part_count=1,
            measure_count=0,
            staff_count=0,
        )

        with patch(
            "pipeline.transform._transform.MusicXmlValidator.validate",
            return_value=validation_result,
        ):
            with patch(
                "pipeline.transform._transform._evaluate_quality_gate",
                return_value=(True, ["tab_staff_missing"]),
            ):
                with patch(
                    "pipeline.transform._transform.GuitarFixer.apply",
                    side_effect=ValueError("boom"),
                ):
                    with pytest.raises(TransformError, match="Unexpected transform failure"):
                        transform(musicxml_path, output_dir)


class TestTransformPublicApi:
    def test_transform_importable_from_transform_package(self) -> None:
        from pipeline.transform import transform

        assert callable(transform)
