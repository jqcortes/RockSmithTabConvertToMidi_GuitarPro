"""MusicXmlValidator - validate plain MusicXML input."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import zipfile

from lxml import etree

from pipeline.common import get_logger
from pipeline.transform.errors import TransformValidationError

_LOG = get_logger(__name__)
_VALID_ROOTS = {"score-partwise", "score-timewise"}


@dataclass(frozen=True)
class ValidationResult:
    """Validated MusicXML metadata and parsed tree."""

    tree: etree._ElementTree
    part_count: int
    measure_count: int
    staff_count: int


class MusicXmlValidator:
    """Validate plain MusicXML files and return parsed metadata."""

    @staticmethod
    def validate(path: Path) -> ValidationResult:
        """Load and validate a plain `.xml` MusicXML file.

        Raises:
            TransformValidationError: ファイル不在・XML 不正・ルート要素不正
        """
        if not path.exists():
            raise TransformValidationError(
                f"MusicXML ファイルが見つかりません: {path}"
            )

        tree = MusicXmlValidator._load_tree(path)

        root = tree.getroot()
        root_name = MusicXmlValidator._local_name(root.tag)
        if root_name not in _VALID_ROOTS:
            raise TransformValidationError(
                f"MusicXML のルート要素が不正です: {root_name}"
            )

        result = ValidationResult(
            tree=tree,
            part_count=len(tree.xpath("//*[local-name()='part']")),
            measure_count=len(tree.xpath("//*[local-name()='measure']")),
            staff_count=MusicXmlValidator._count_staves(tree),
        )

        _LOG.info(
            "transform_xml_validated",
            path=str(path),
            part_count=result.part_count,
            measure_count=result.measure_count,
            staff_count=result.staff_count,
        )
        return result

    @staticmethod
    def _load_tree(path: Path) -> etree._ElementTree:
        """Load `.xml` or `.mxl` MusicXML content into an ElementTree."""
        if path.suffix.lower() == ".mxl":
            return MusicXmlValidator._load_mxl_tree(path)

        try:
            return etree.parse(str(path))  # noqa: S320  # ローカルファイルのみ
        except etree.XMLSyntaxError as exc:
            raise TransformValidationError(
                f"MusicXML が well-formed ではありません: {path}"
            ) from exc
        except OSError as exc:
            raise TransformValidationError(
                f"MusicXML を読み込めませんでした: {path}"
            ) from exc

    @staticmethod
    def _load_mxl_tree(path: Path) -> etree._ElementTree:
        """Load the first XML entry from an `.mxl` archive."""
        try:
            with zipfile.ZipFile(path, "r") as archive:
                xml_names = [name for name in archive.namelist() if name.endswith(".xml")]
                if not xml_names:
                    raise TransformValidationError(
                        f".mxl 内に XML ファイルが見つかりません: {path}"
                    )
                xml_content = archive.read(xml_names[0])
        except zipfile.BadZipFile as exc:
            raise TransformValidationError(
                f".mxl ファイルが ZIP 形式ではありません: {path}"
            ) from exc
        except OSError as exc:
            raise TransformValidationError(
                f".mxl ファイルを読み込めませんでした: {path}"
            ) from exc

        try:
            root = etree.fromstring(xml_content)
        except etree.XMLSyntaxError as exc:
            raise TransformValidationError(
                f"MusicXML が well-formed ではありません: {path}"
            ) from exc

        return etree.ElementTree(root)

    @staticmethod
    def _count_staves(tree: etree._ElementTree) -> int:
        """Count distinct staves across parts for metrics."""
        note_nodes = tree.xpath("//*[local-name()='note'][.//*[local-name()='staff']]")
        seen: set[tuple[str, str]] = set()
        for note in note_nodes:
            staff = note.xpath("string(.//*[local-name()='staff'][1])").strip()
            part_id = note.xpath("string(ancestor::*[local-name()='part'][1]/@id)").strip()
            if staff:
                seen.add((part_id, staff))

        if seen:
            return len(seen)

        staves_values = [
            int(value)
            for value in tree.xpath("//*[local-name()='staves']/text()")
            if value.isdigit()
        ]
        if staves_values:
            return max(staves_values)

        part_count = len(tree.xpath("//*[local-name()='part']"))
        return part_count if part_count > 0 else 0

    @staticmethod
    def _local_name(tag: Any) -> str:
        """Return XML local name regardless of namespace presence."""
        if hasattr(tag, "localname"):
            return str(tag.localname)
        if isinstance(tag, (bytes, bytearray)):
            tag = tag.decode("utf-8")
        tag_str = str(tag)
        if tag_str.startswith("{"):
            return tag_str.split("}", maxsplit=1)[1]
        return tag_str