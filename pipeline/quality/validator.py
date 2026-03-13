"""Input validation for the Quality domain."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lxml import etree
from mido import MidiFile

from pipeline.quality.errors import QualityValidationError


@dataclass(frozen=True)
class QualityValidationResult:
    """Validated inputs for the Quality scoring workflow."""

    musicxml_path: Path
    midi_path: Path
    tree: etree._ElementTree
    midi_file: MidiFile


class QualityInputValidator:
    """Validate MusicXML and MIDI inputs before scoring."""

    @staticmethod
    def validate(musicxml_path: Path, midi_path: Path) -> QualityValidationResult:
        """Validate and load MusicXML plus MIDI inputs."""
        if not musicxml_path.exists():
            raise QualityValidationError(f"MusicXML input not found: {musicxml_path}")
        if not midi_path.exists():
            raise QualityValidationError(f"MIDI input not found: {midi_path}")

        try:
            tree = etree.parse(str(musicxml_path))
        except (OSError, etree.XMLSyntaxError) as exc:
            raise QualityValidationError(f"Failed to parse MusicXML: {musicxml_path}") from exc

        try:
            midi_file = MidiFile(str(midi_path))
        except (OSError, EOFError, ValueError, IndexError) as exc:
            raise QualityValidationError(f"Failed to read MIDI: {midi_path}") from exc

        return QualityValidationResult(
            musicxml_path=musicxml_path,
            midi_path=midi_path,
            tree=tree,
            midi_file=midi_file,
        )