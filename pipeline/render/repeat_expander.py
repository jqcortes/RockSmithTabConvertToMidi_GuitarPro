"""MusicXML repeat/navigation expansion for linear MIDI rendering."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree


@dataclass(frozen=True)
class RepeatExpansionResult:
    """Expanded measure sequence and any safety warnings."""

    measures: list[etree._Element]
    warnings: list[str]


@dataclass
class RepeatExpansionContext:
    """Mutable cross-page state for repeat expansion per part."""

    # Measures captured from a forward-repeat start until its backward-repeat close.
    # Keyed by part id so each instrument is tracked independently.
    open_repeat_segment_by_part: dict[str, list[etree._Element]]

    @staticmethod
    def empty() -> "RepeatExpansionContext":
        return RepeatExpansionContext(open_repeat_segment_by_part={})


class RepeatExpander:
    """Expand repeat/ending/barline + navigation markers into a linear measure sequence."""

    @staticmethod
    def expand_part_measures(part: etree._Element, *, max_visits_per_measure: int = 8) -> RepeatExpansionResult:
        measures = list(part.xpath("./*[local-name()='measure']"))
        if not measures:
            return RepeatExpansionResult(measures=[], warnings=[])

        segno_idx = RepeatExpander._find_segno_index(measures)
        coda_idx = RepeatExpander._find_coda_index(measures)

        expanded: list[etree._Element] = []
        warnings: list[str] = []
        visits: dict[int, int] = {}
        repeat_counts: dict[int, int] = {}
        repeat_stack: list[int] = []

        used_dacapo = False
        used_dalsegno = False
        used_tocoda = False
        after_navigation_jump = False

        index = 0
        while 0 <= index < len(measures):
            visits[index] = visits.get(index, 0) + 1
            if visits[index] > max_visits_per_measure:
                warnings.append(
                    f"repeat expansion safety stop at measure index={index} (possible infinite loop)"
                )
                break

            measure = measures[index]

            if RepeatExpander._has_forward_repeat(measure):
                if not repeat_stack or repeat_stack[-1] != index:
                    repeat_stack.append(index)

            active_repeat_start = repeat_stack[-1] if repeat_stack else 0
            current_pass = repeat_counts.get(active_repeat_start, 0) + 1
            ending_numbers = RepeatExpander._ending_numbers(measure)
            if not ending_numbers or current_pass in ending_numbers:
                expanded.append(measure)

            sound = RepeatExpander._sound_attrs(measure)

            if sound["fine"] and after_navigation_jump:
                break

            if sound["dacapo"] and not used_dacapo:
                used_dacapo = True
                after_navigation_jump = True
                index = 0
                continue

            if sound["dalsegno"] and not used_dalsegno:
                used_dalsegno = True
                after_navigation_jump = True
                if segno_idx is None:
                    warnings.append("dalsegno encountered but no segno marker found")
                    index = 0
                else:
                    index = segno_idx
                continue

            if sound["tocoda"] and after_navigation_jump and not used_tocoda:
                if coda_idx is None:
                    warnings.append("tocoda encountered but no coda marker found")
                else:
                    used_tocoda = True
                    index = coda_idx
                    continue

            if RepeatExpander._has_backward_repeat(measure):
                repeat_start = repeat_stack[-1] if repeat_stack else 0
                count = repeat_counts.get(repeat_start, 0)
                if count < 1:
                    repeat_counts[repeat_start] = count + 1
                    index = repeat_start
                    continue
                if repeat_stack and repeat_stack[-1] == repeat_start:
                    repeat_stack.pop()

            index += 1

        return RepeatExpansionResult(measures=expanded, warnings=warnings)

    @staticmethod
    def expand_part_measures_with_context(
        part: etree._Element,
        *,
        part_id: str,
        context: RepeatExpansionContext,
        max_visits_per_measure: int = 8,
    ) -> RepeatExpansionResult:
        """Expand measures and apply cross-page repeat bridging via mutable context."""
        base = RepeatExpander.expand_part_measures(part, max_visits_per_measure=max_visits_per_measure)
        measures = list(part.xpath("./*[local-name()='measure']"))
        if not measures:
            return base

        has_forward_in_page = any(RepeatExpander._has_forward_repeat(measure) for measure in measures)
        has_backward_in_page = any(RepeatExpander._has_backward_repeat(measure) for measure in measures)

        open_segment = context.open_repeat_segment_by_part.get(part_id)

        # If this page declares a new forward repeat, start tracking from the first forward marker.
        if has_forward_in_page:
            first_forward_idx = next(
                idx for idx, measure in enumerate(measures) if RepeatExpander._has_forward_repeat(measure)
            )
            open_segment = list(measures[first_forward_idx:])
            # If the same page also closes with backward repeat, local expansion already handled replay.
            if has_backward_in_page:
                context.open_repeat_segment_by_part.pop(part_id, None)
            else:
                context.open_repeat_segment_by_part[part_id] = open_segment
            return base

        # Continue tracking from prior pages when no local forward marker exists.
        if open_segment is not None:
            open_segment = list(open_segment) + list(measures)

            # Cross-page close: backward repeat appears without local forward.
            if has_backward_in_page:
                context.open_repeat_segment_by_part.pop(part_id, None)
                # Use current page raw measures once, then replay captured cross-page segment.
                # This avoids local fallback duplicating backward-only pages.
                bridged = list(measures) + open_segment
                warnings = list(base.warnings) + [
                    "cross-page repeat bridged from previous page context"
                ]
                return RepeatExpansionResult(measures=bridged, warnings=warnings)

            context.open_repeat_segment_by_part[part_id] = open_segment

        return base

    @staticmethod
    def _sound_attrs(measure: etree._Element) -> dict[str, bool]:
        sounds = measure.xpath(".//*[local-name()='sound']")

        def _flag(name: str) -> bool:
            for sound in sounds:
                value = str(sound.get(name, "")).strip().lower()
                if value not in {"", "no", "false", "0"}:
                    return True
            return False

        return {
            "dacapo": _flag("dacapo"),
            "dalsegno": _flag("dalsegno"),
            "tocoda": _flag("tocoda"),
            "fine": _flag("fine"),
        }

    @staticmethod
    def _has_forward_repeat(measure: etree._Element) -> bool:
        return bool(
            measure.xpath(
                "./*[local-name()='barline']/*[local-name()='repeat'][translate(@direction,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='forward']"
            )
        )

    @staticmethod
    def _has_backward_repeat(measure: etree._Element) -> bool:
        return bool(
            measure.xpath(
                "./*[local-name()='barline']/*[local-name()='repeat'][translate(@direction,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='backward']"
            )
        )

    @staticmethod
    def _ending_numbers(measure: etree._Element) -> set[int]:
        endings = measure.xpath("./*[local-name()='barline']/*[local-name()='ending']/@number")
        parsed: set[int] = set()
        for ending_value in endings:
            for token in str(ending_value).replace(" ", "").split(","):
                if token.isdigit():
                    parsed.add(int(token))
        return parsed

    @staticmethod
    def _find_segno_index(measures: list[etree._Element]) -> int | None:
        for index, measure in enumerate(measures):
            has_segno = bool(
                measure.xpath(
                    ".//*[local-name()='direction-type']/*[local-name()='segno'] | .//*[local-name()='sound'][@segno]"
                )
            )
            if has_segno:
                return index
        return None

    @staticmethod
    def _find_coda_index(measures: list[etree._Element]) -> int | None:
        for index, measure in enumerate(measures):
            has_coda = bool(
                measure.xpath(
                    ".//*[local-name()='direction-type']/*[local-name()='coda'] | .//*[local-name()='sound'][@coda]"
                )
            )
            if has_coda:
                return index
        return None
