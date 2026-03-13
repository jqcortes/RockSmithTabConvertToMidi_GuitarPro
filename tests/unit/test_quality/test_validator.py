"""tests for Quality input validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree
from mido import MidiFile


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml"


class TestQualityInputValidator:
    def test_validate_returns_parsed_musicxml_and_midi(self, tmp_path: Path) -> None:
        from pipeline.quality.validator import QualityInputValidator

        midi_path = tmp_path / "valid.mid"
        MidiFile(type=1).save(midi_path)

        result = QualityInputValidator.validate(FIXTURES_DIR / "render_multipart.xml", midi_path)

        assert isinstance(result.tree, etree._ElementTree)
        assert isinstance(result.midi_file, MidiFile)
        assert result.musicxml_path == FIXTURES_DIR / "render_multipart.xml"
        assert result.midi_path == midi_path

    def test_validate_raises_for_missing_musicxml(self, tmp_path: Path) -> None:
        from pipeline.quality.errors import QualityValidationError
        from pipeline.quality.validator import QualityInputValidator

        midi_path = tmp_path / "valid.mid"
        MidiFile(type=1).save(midi_path)

        with pytest.raises(QualityValidationError, match="MusicXML input not found"):
            QualityInputValidator.validate(tmp_path / "missing.xml", midi_path)

    def test_validate_raises_for_invalid_musicxml(self, tmp_path: Path) -> None:
        from pipeline.quality.errors import QualityValidationError
        from pipeline.quality.validator import QualityInputValidator

        invalid_xml = tmp_path / "invalid.xml"
        invalid_xml.write_text("<score-partwise>", encoding="utf-8")
        midi_path = tmp_path / "valid.mid"
        MidiFile(type=1).save(midi_path)

        with pytest.raises(QualityValidationError, match="Failed to parse MusicXML"):
            QualityInputValidator.validate(invalid_xml, midi_path)

    def test_validate_raises_for_missing_midi(self, tmp_path: Path) -> None:
        from pipeline.quality.errors import QualityValidationError
        from pipeline.quality.validator import QualityInputValidator

        with pytest.raises(QualityValidationError, match="MIDI input not found"):
            QualityInputValidator.validate(FIXTURES_DIR / "render_multipart.xml", tmp_path / "missing.mid")

    def test_validate_raises_for_invalid_midi(self, tmp_path: Path) -> None:
        from pipeline.quality.errors import QualityValidationError
        from pipeline.quality.validator import QualityInputValidator

        invalid_midi = tmp_path / "invalid.mid"
        invalid_midi.write_bytes(b"not-a-midi")

        with pytest.raises(QualityValidationError, match="Failed to read MIDI"):
            QualityInputValidator.validate(FIXTURES_DIR / "render_multipart.xml", invalid_midi)