"""PartIdentifier - infer logical part roles from MusicXML."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from lxml import etree

from pipeline.common import get_logger

PartRole = Literal["guitar", "bass", "drums", "other"]
_TRANSFORM_NAMESPACE = "https://band-score-to-midi/transform"
_LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class PartInfo:
    """Resolved logical part information."""

    part_id: str
    part_name: str
    role: PartRole
    tab_staff_id: str | None


@dataclass(frozen=True)
class PartIdentifierResult:
    """Resolved part role mapping and warnings."""

    parts: list[PartInfo]
    parts_map: dict[str, PartRole]
    warnings: list[str]


class PartIdentifier:
    """Infer MusicXML logical part roles and annotate XML."""

    @staticmethod
    def identify(
        tree: etree._ElementTree,
        *,
        default_role: PartRole = "other",
    ) -> PartIdentifierResult:
        """Inspect part-list and part content to infer roles.

        Args:
            tree: lxml ElementTree of the MusicXML document.
            default_role: Fallback role when no identifier clue is found.
                          Defaults to ``"other"``.
        """
        part_meta = PartIdentifier._part_metadata(tree)
        resolved_parts: list[PartInfo] = []
        parts_map: dict[str, PartRole] = {}
        warnings: list[str] = []

        for part in tree.xpath("//*[local-name()='part']"):
            part_id = PartIdentifier._string_value(part.xpath("@id"))
            meta = part_meta.get(part_id, {})
            part_name = str(meta.get("part_name", "")).strip() or part_id
            instrument_name = str(meta.get("instrument_name", "")).strip()
            tab_staff_id = PartIdentifier._detect_tab_staff(part)
            role = PartIdentifier._infer_role(part_name, instrument_name, part, tab_staff_id, default_role=default_role)
            if role == "other":
                warnings.append(part_name)
            info = PartInfo(
                part_id=part_id,
                part_name=part_name,
                role=role,
                tab_staff_id=tab_staff_id,
            )
            resolved_parts.append(info)
            parts_map[part_id] = role

        _LOGGER.info("part_identifier_complete", part_count=len(resolved_parts), warnings=len(warnings))
        return PartIdentifierResult(parts=resolved_parts, parts_map=parts_map, warnings=warnings)

    @staticmethod
    def annotate(
        tree: etree._ElementTree,
        result: PartIdentifierResult,
    ) -> etree._ElementTree:
        """Annotate part nodes with transform role attribute."""
        root = tree.getroot()
        namespace_map = dict(root.nsmap)
        if "transform" not in namespace_map.values() and "transform" not in namespace_map:
            namespace_map.setdefault("transform", _TRANSFORM_NAMESPACE)
        for part in tree.xpath("//*[local-name()='part']"):
            part_id = PartIdentifier._string_value(part.xpath("@id"))
            role = result.parts_map.get(part_id)
            if role is not None:
                part.set(f"{{{_TRANSFORM_NAMESPACE}}}role", role)
        return tree

    @staticmethod
    def _part_metadata(tree: etree._ElementTree) -> dict[str, dict[str, str]]:
        """Read part-list metadata keyed by score-part id."""
        metadata: dict[str, dict[str, str]] = {}
        for score_part in tree.xpath("//*[local-name()='part-list']/*[local-name()='score-part']"):
            part_id = PartIdentifier._string_value(score_part.xpath("@id"))
            metadata[part_id] = {
                "part_name": PartIdentifier._string_value(score_part.xpath("./*[local-name()='part-name']/text()")),
                "instrument_name": PartIdentifier._string_value(
                    score_part.xpath("./*[local-name()='score-instrument'][1]/*[local-name()='instrument-name']/text()")
                ),
            }
        return metadata

    @staticmethod
    def _detect_tab_staff(part: Any) -> str | None:
        """Detect TAB staff number if present."""
        for details in part.xpath(
            ".//*[local-name()='staff-details'][number(*[local-name()='staff-lines'])=6]"
        ):
            number = PartIdentifier._string_value(details.xpath("@number"))
            if number:
                return number
        for clef in part.xpath(".//*[local-name()='clef']"):
            sign_text = PartIdentifier._string_value(clef.xpath("./*[local-name()='sign']/text()"))
            sign_attr = PartIdentifier._string_value(clef.xpath("@sign"))
            if sign_text.lower() == "tab" or sign_attr.lower() == "tab":
                return PartIdentifier._string_value(clef.xpath("@number")) or "1"
        return None

    @staticmethod
    def _infer_role(
        part_name: str,
        instrument_name: str,
        part: Any,
        tab_staff_id: str | None,
        *,
        default_role: PartRole = "other",
    ) -> PartRole:
        """Infer part role from metadata and clef/tab evidence."""
        combined = f"{part_name} {instrument_name}".lower()
        clef_signs = " ".join(
            PartIdentifier._string_value(clef.xpath("./*[local-name()='sign']/text()"))
            for clef in part.xpath(".//*[local-name()='clef']")
        ).lower()
        if "bass" in combined and tab_staff_id is None:
            return "bass"
        if "guitar" in combined or tab_staff_id is not None:
            return "guitar"
        if "bass" in combined:
            return "bass"
        if "drum" in combined or "perc" in combined or "percussion" in clef_signs:
            return "drums"
        return default_role

    @staticmethod
    def _string_value(value: Any) -> str:
        """Normalize xpath output to string."""
        if isinstance(value, list):
            if not value:
                return ""
            return PartIdentifier._string_value(value[0])
        if value is None:
            return ""
        return str(value).strip()
