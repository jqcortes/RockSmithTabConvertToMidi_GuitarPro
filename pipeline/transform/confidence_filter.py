"""ConfidenceFilter - remove low-confidence notes from MusicXML."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from lxml import etree


@dataclass(frozen=True)
class RemovedNote:
    """Metadata describing a removed note."""

    measure: str
    part_id: str
    pitch: str
    confidence: float


@dataclass
class FilterResult:
    """Result of confidence filtering."""

    tree: etree._ElementTree
    removed: list[RemovedNote] = field(default_factory=list)
    total: int = 0

    @property
    def filter_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return len(self.removed) / self.total


class ConfidenceFilter:
    """Remove notes whose confidence attribute is below threshold."""

    THRESHOLD: ClassVar[float] = 0.5

    @staticmethod
    def filter(tree: etree._ElementTree) -> FilterResult:
        """Filter low-confidence notes in-place and return metadata."""
        removed: list[RemovedNote] = []
        notes = tree.xpath("//*[local-name()='note']")
        total = len(notes)
        for note in list(notes):
            confidence_text = ConfidenceFilter._string_value(note.xpath("@confidence"))
            if confidence_text == "":
                continue
            confidence = float(confidence_text)
            if confidence >= ConfidenceFilter.THRESHOLD:
                continue

            part_id = ConfidenceFilter._string_value(note.xpath("string(ancestor::*[local-name()='part'][1]/@id)"))
            measure = ConfidenceFilter._string_value(note.xpath("string(ancestor::*[local-name()='measure'][1]/@number)"))
            step = ConfidenceFilter._string_value(note.xpath("string(./*[local-name()='pitch']/*[local-name()='step'])"))
            octave = ConfidenceFilter._string_value(note.xpath("string(./*[local-name()='pitch']/*[local-name()='octave'])"))
            removed.append(
                RemovedNote(
                    measure=measure,
                    part_id=part_id,
                    pitch=f"{step}{octave}",
                    confidence=confidence,
                )
            )
            parent = note.getparent()
            if parent is not None:
                parent.remove(note)

        return FilterResult(tree=tree, removed=removed, total=total)

    @staticmethod
    def _string_value(value: Any) -> str:
        """Normalize xpath output to string."""
        if isinstance(value, list):
            if not value:
                return ""
            return ConfidenceFilter._string_value(value[0])
        if value is None:
            return ""
        return str(value).strip()