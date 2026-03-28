"""TAB OCR helpers backed by an external Tesseract executable."""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from pipeline.common import get_logger
from pipeline.transform.errors import TransformTabOcrError

_LOGGER = get_logger(__name__)
_MIN_CONFIDENCE = 30.0
_MAX_FRET = 24
_DEFAULT_TESSERACT_LOCATIONS = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)


@dataclass(frozen=True)
class TabOcrToken:
    """Single OCR-detected TAB fret token."""

    staff_group: int
    string: int
    fret: int
    x: int
    y: int
    confidence: float


@dataclass(frozen=True)
class TabOcrResult:
    """OCR scan result for a preprocessed TAB page image."""

    tokens: list[TabOcrToken]
    warnings: list[str]
    tesseract_path: Path | None


class TabOcrScanner:
    """Extract TAB fret numbers from a preprocessed score image."""

    @staticmethod
    def extract_tokens(
        image_path: Path,
        *,
        tesseract_path: Path | None = None,
    ) -> TabOcrResult:
        """Run OCR on the image and map digit tokens onto TAB strings."""
        resolved_tesseract = TabOcrScanner._resolve_tesseract_path(tesseract_path)
        if resolved_tesseract is None:
            return TabOcrResult(
                tokens=[],
                warnings=["TAB OCR skipped: tesseract executable not found"],
                tesseract_path=None,
            )

        staff_groups = TabOcrScanner._detect_tab_staff_groups(image_path)
        if len(staff_groups) == 0:
            return TabOcrResult(
                tokens=[],
                warnings=["TAB OCR skipped: no 6-line TAB staff detected in image"],
                tesseract_path=resolved_tesseract,
            )

        tsv_text = TabOcrScanner._run_tesseract_tsv(image_path, resolved_tesseract)
        page_tokens = TabOcrScanner._parse_tsv_tokens(tsv_text, staff_groups)
        row_tokens = TabOcrScanner._scan_tokens_by_staff_rows(
            image_path,
            tesseract_path=resolved_tesseract,
            staff_groups=staff_groups,
        )
        tokens = TabOcrScanner._deduplicate_tokens([*page_tokens, *row_tokens])
        _LOGGER.info(
            "tab_ocr_complete",
            image_path=str(image_path),
            tesseract_path=str(resolved_tesseract),
            detected_tokens=len(tokens),
            detected_staff_groups=len(staff_groups),
            page_tokens=len(page_tokens),
            row_tokens=len(row_tokens),
        )
        return TabOcrResult(tokens=tokens, warnings=[], tesseract_path=resolved_tesseract)

    @staticmethod
    def _resolve_tesseract_path(explicit_path: Path | None) -> Path | None:
        if explicit_path is not None:
            return explicit_path if explicit_path.exists() else None

        env_path = os.environ.get("TESSERACT_PATH", "").strip()
        if env_path:
            candidate = Path(env_path)
            if candidate.exists():
                return candidate

        discovered = shutil.which("tesseract")
        if discovered is None:
            local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
            default_locations = list(_DEFAULT_TESSERACT_LOCATIONS)
            if local_appdata:
                default_locations.append(
                    Path(local_appdata) / "Programs" / "Tesseract-OCR" / "tesseract.exe"
                )
            for candidate in default_locations:
                if candidate.exists():
                    return candidate
            return None
        return Path(discovered)

    @staticmethod
    def _run_tesseract_tsv(image_path: Path, tesseract_path: Path) -> str:
        return TabOcrScanner._run_tesseract_tsv_with_config(
            image_path,
            tesseract_path,
            psm=11,
        )

    @staticmethod
    def _run_tesseract_tsv_with_config(
        image_path: Path,
        tesseract_path: Path,
        *,
        psm: int,
    ) -> str:
        command = [
            str(tesseract_path),
            str(image_path),
            "stdout",
            "--psm",
            str(psm),
            "-c",
            "tessedit_char_whitelist=0123456789",
            "tsv",
        ]
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as exc:
            raise TransformTabOcrError(f"Failed to run tesseract: {exc}") from exc
        return completed.stdout

    @staticmethod
    def _detect_tab_staff_groups(image_path: Path) -> list[list[int]]:
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise TransformTabOcrError(f"Could not read image for TAB OCR: {image_path}")

        _, binary = cv2.threshold(
            image,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )
        kernel_width = max(25, image.shape[1] // 8)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)

        contours, _hierarchy = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        line_centers: list[int] = []
        min_width = image.shape[1] * 0.15
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            if width < min_width or height > 6:
                continue
            line_centers.append(y + (height // 2))

        collapsed = TabOcrScanner._collapse_close_positions(line_centers, tolerance=4)
        return TabOcrScanner._group_tab_lines(collapsed)

    @staticmethod
    def _collapse_close_positions(values: Sequence[int], *, tolerance: int) -> list[int]:
        if len(values) == 0:
            return []
        clusters: list[list[int]] = [[value] for value in sorted(values)]
        collapsed: list[list[int]] = [clusters[0]]
        for cluster in clusters[1:]:
            if abs(cluster[0] - collapsed[-1][-1]) <= tolerance:
                collapsed[-1].extend(cluster)
            else:
                collapsed.append(cluster)
        return [int(round(sum(cluster) / len(cluster))) for cluster in collapsed]

    @staticmethod
    def _group_tab_lines(line_centers: Sequence[int]) -> list[list[int]]:
        groups: list[list[int]] = []
        if len(line_centers) < 6:
            return groups

        index = 0
        while index + 5 < len(line_centers):
            candidate = list(line_centers[index : index + 6])
            spacings = np.diff(candidate)
            if len(spacings) == 5 and min(spacings) > 0:
                median_spacing = float(np.median(spacings))
                if all(abs(int(spacing) - median_spacing) <= max(3, median_spacing * 0.45) for spacing in spacings):
                    groups.append(candidate)
                    index += 6
                    continue
            index += 1
        return groups

    @staticmethod
    def _parse_tsv_tokens(
        tsv_text: str,
        staff_groups: Sequence[Sequence[int]],
    ) -> list[TabOcrToken]:
        reader = csv.DictReader(tsv_text.splitlines(), delimiter="\t")
        tokens: list[TabOcrToken] = []
        for row in reader:
            text = str(row.get("text", "")).strip()
            if not text.isdigit():
                continue

            fret = int(text)
            if fret < 0 or fret > _MAX_FRET:
                continue

            confidence_text = str(row.get("conf", "")).strip()
            try:
                confidence = float(confidence_text)
            except ValueError:
                continue
            if confidence < _MIN_CONFIDENCE:
                continue

            left = TabOcrScanner._int_field(row, "left")
            top = TabOcrScanner._int_field(row, "top")
            width = TabOcrScanner._int_field(row, "width")
            height = TabOcrScanner._int_field(row, "height")
            center_x = left + (width // 2)
            center_y = top + (height // 2)
            assignment = TabOcrScanner._assign_token_to_staff(center_y, staff_groups)
            if assignment is None:
                continue

            staff_group, string = assignment
            tokens.append(
                TabOcrToken(
                    staff_group=staff_group,
                    string=string,
                    fret=fret,
                    x=center_x,
                    y=center_y,
                    confidence=confidence,
                )
            )

        return sorted(tokens, key=lambda token: (token.staff_group, token.x, token.y))

    @staticmethod
    def _scan_tokens_by_staff_rows(
        image_path: Path,
        *,
        tesseract_path: Path,
        staff_groups: Sequence[Sequence[int]],
    ) -> list[TabOcrToken]:
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise TransformTabOcrError(f"Could not read image for TAB OCR: {image_path}")

        height, width = image.shape
        tokens: list[TabOcrToken] = []
        x_margin = max(10, width // 14)

        for staff_group_index, staff_lines in enumerate(staff_groups):
            if len(staff_lines) != 6:
                continue

            spacing_candidates = np.diff(staff_lines)
            spacing = float(np.median(spacing_candidates)) if len(spacing_candidates) > 0 else 0.0
            half_height = max(int(spacing * 0.5), 4)

            for line_index, line_y in enumerate(staff_lines):
                y1 = max(0, line_y - half_height)
                y2 = min(height, line_y + half_height)
                if y2 <= y1:
                    continue

                strip = image[y1:y2, x_margin:]
                if strip.size == 0:
                    continue

                scale = max(3, int(40 / max(1, strip.shape[0])))
                upscaled = cv2.resize(strip, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                _, binary = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                # Remove the TAB line running through the strip center so OCR can focus on digits.
                center = binary.shape[0] // 2
                band = max(1, binary.shape[0] // 12)
                binary[max(0, center - band) : min(binary.shape[0], center + band + 1), :] = 255

                with tempfile.TemporaryDirectory() as temp_dir:
                    strip_path = Path(temp_dir) / "tab_row.png"
                    ok, encoded = cv2.imencode(".png", binary)
                    if not ok:
                        continue
                    strip_path.write_bytes(encoded.tobytes())
                    tsv_text = TabOcrScanner._run_tesseract_tsv_with_config(
                        strip_path,
                        tesseract_path,
                        psm=7,
                    )

                tokens.extend(
                    TabOcrScanner._parse_row_tsv_tokens(
                        tsv_text,
                        staff_group=staff_group_index,
                        string=6 - line_index,
                        x_offset=x_margin,
                        y_offset=y1,
                        scale=scale,
                    )
                )

        return tokens

    @staticmethod
    def _parse_row_tsv_tokens(
        tsv_text: str,
        *,
        staff_group: int,
        string: int,
        x_offset: int,
        y_offset: int,
        scale: int,
    ) -> list[TabOcrToken]:
        reader = csv.DictReader(tsv_text.splitlines(), delimiter="\t")
        tokens: list[TabOcrToken] = []
        for row in reader:
            text = str(row.get("text", "")).strip()
            if not text.isdigit() or len(text) > 2:
                continue

            fret = int(text)
            if fret < 0 or fret > _MAX_FRET:
                continue

            confidence_text = str(row.get("conf", "")).strip()
            try:
                confidence = float(confidence_text)
            except ValueError:
                continue
            if confidence < _MIN_CONFIDENCE:
                continue

            left = TabOcrScanner._int_field(row, "left")
            top = TabOcrScanner._int_field(row, "top")
            width = TabOcrScanner._int_field(row, "width")
            height = TabOcrScanner._int_field(row, "height")
            center_x = x_offset + ((left + (width // 2)) // max(scale, 1))
            center_y = y_offset + ((top + (height // 2)) // max(scale, 1))
            tokens.append(
                TabOcrToken(
                    staff_group=staff_group,
                    string=string,
                    fret=fret,
                    x=center_x,
                    y=center_y,
                    confidence=confidence,
                )
            )

        return tokens

    @staticmethod
    def _deduplicate_tokens(tokens: Sequence[TabOcrToken]) -> list[TabOcrToken]:
        deduplicated: list[TabOcrToken] = []
        for token in sorted(tokens, key=lambda item: (item.staff_group, item.string, item.x, item.y)):
            duplicate_index: int | None = None
            for index, existing in enumerate(deduplicated):
                if existing.staff_group != token.staff_group or existing.string != token.string:
                    continue
                if abs(existing.x - token.x) <= 8 and abs(existing.y - token.y) <= 8:
                    duplicate_index = index
                    break

            if duplicate_index is None:
                deduplicated.append(token)
                continue

            if token.confidence > deduplicated[duplicate_index].confidence:
                deduplicated[duplicate_index] = token

        return sorted(deduplicated, key=lambda token: (token.staff_group, token.x, token.y))

    @staticmethod
    def _assign_token_to_staff(
        center_y: int,
        staff_groups: Sequence[Sequence[int]],
    ) -> tuple[int, int] | None:
        best_match: tuple[int, int] | None = None
        best_distance: float | None = None

        for staff_group_index, staff_lines in enumerate(staff_groups):
            if len(staff_lines) != 6:
                continue

            spacing_candidates = np.diff(staff_lines)
            spacing = float(np.median(spacing_candidates)) if len(spacing_candidates) > 0 else 0.0
            max_distance = max(6.0, spacing * 0.8)

            for line_index, line_y in enumerate(staff_lines):
                distance = abs(center_y - line_y)
                if distance > max_distance:
                    continue
                if best_distance is None or distance < best_distance:
                    best_distance = float(distance)
                    best_match = (staff_group_index, 6 - line_index)

        return best_match

    @staticmethod
    def _int_field(row: dict[str, str], key: str) -> int:
        value = str(row.get(key, "0")).strip()
        return int(value) if value.isdigit() else 0
