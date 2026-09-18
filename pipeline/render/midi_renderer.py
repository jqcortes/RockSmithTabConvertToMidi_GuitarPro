"""MusicXML to MIDI Type 1 rendering for the Render domain."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lxml import etree
from mido import Message, MetaMessage, MidiFile, MidiTrack

from pipeline.render.channel_mapper import ChannelAssignment, ChannelMapper, PartRole, RenderPartInfo
from pipeline.render.errors import RenderValidationError
from pipeline.render.repeat_expander import RepeatExpander, RepeatExpansionContext
from pipeline.render.technique_renderer import TechniqueRenderer
from pipeline.render.tempo_resolver import TempoResolver


@dataclass(frozen=True)
class MidiRenderResult:
    """Summary of a completed MIDI render operation."""

    output_path: Path
    channel_map: dict[str, str]
    tempo_events: int
    techniques_rendered: int
    warnings: list[str]


class MidiRenderer:
    """Render a transformed MusicXML file into MIDI Type 1."""

    @staticmethod
    def render_score(
        musicxml_path: Path,
        output_path: Path,
        *,
        default_bpm: int = 120,
        pitch_bend_range: int = 2,
        repeat_context: RepeatExpansionContext | None = None,
    ) -> MidiRenderResult:
        """Read MusicXML, create MIDI Type 1 tracks, and write the result."""
        tree = MidiRenderer._load_tree(musicxml_path)
        midi_file = MidiFile(type=1, ticks_per_beat=480)

        tempo_result = TempoResolver.build_meta_track(tree, default_bpm=default_bpm)
        midi_file.tracks.append(tempo_result.track)
        render_warnings = list(tempo_result.warnings)
        local_repeat_context = repeat_context if repeat_context is not None else RepeatExpansionContext.empty()

        part_infos = MidiRenderer._extract_part_infos(tree)
        assignments = ChannelMapper.assign(part_infos)
        assignment_map = {assignment.part_id: assignment for assignment in assignments}
        techniques_rendered = 0

        for part in tree.xpath("//*[local-name()='part']"):
            part_id = MidiRenderer._string_value(part.xpath("@id"))
            if part_id == "":
                continue
            assignment = assignment_map.get(part_id)
            if assignment is None:
                continue

            track = MidiTrack()
            track.append(MetaMessage("track_name", name=MidiRenderer._part_name(tree, part_id), time=0))
            if assignment.midi_program is not None:
                track.append(
                    Message(
                        "program_change",
                        channel=assignment.midi_channel - 1,
                        program=assignment.midi_program,
                        time=0,
                    )
                )

            # Collect events as (abs_tick, priority, seq, message).
            # priority: 0=pre-technique, 1=note_on, 2=note_off, 3=post-technique.
            # seq breaks ties within the same (tick, priority) to preserve insertion order.
            events: list[tuple[int, int, int, Message]] = []
            seq = 0
            abs_tick = 0        # absolute tick cursor; advances for non-chord notes
            group_start_tick = 0  # abs tick of the most-recent non-chord note (chord anchor)
            divisions = 1
            # Track open slur numbers to detect hammer-on/pull-off from <slur> arcs.
            # For guitar parts, Audiveris outputs <slur> instead of <hammer-on>/<pull-off>.
            open_slurs: set[str] = set()
            is_guitar_part = assignment.role == "guitar"
            expansion = RepeatExpander.expand_part_measures_with_context(
                part,
                part_id=part_id,
                context=local_repeat_context,
            )
            for warning in expansion.warnings:
                render_warnings.append(f"part={part_id}: {warning}")

            for measure in expansion.measures:
                divisions = MidiRenderer._measure_divisions(measure, divisions)
                for note in measure.xpath("./*[local-name()='note']"):
                    if note.xpath("./*[local-name()='rest']"):
                        continue

                    midi_note = MidiRenderer._pitch_to_midi(note)
                    if midi_note is None:
                        continue

                    is_chord = bool(note.xpath("./*[local-name()='chord']"))
                    duration_value = MidiRenderer._duration_value(note)
                    duration_ticks = max(1, int((duration_value / divisions) * midi_file.ticks_per_beat))

                    # Detect slur stops before calling TechniqueRenderer so the
                    # velocity base can be adjusted for guitar hammer-on/pull-off.
                    slur_stop = False
                    for slur in note.xpath(".//*[local-name()='slur']"):
                        slur_type = slur.get("type", "")
                        slur_number = slur.get("number", "1")
                        if slur_type == "start":
                            open_slurs.add(slur_number)
                        elif slur_type == "stop" and slur_number in open_slurs:
                            open_slurs.discard(slur_number)
                            slur_stop = True

                    # Velocity base: guitar notes that end a slur group are
                    # treated as hammer-on/pull-off (70% velocity by convention).
                    note_velocity = 64
                    if is_guitar_part and slur_stop:
                        note_velocity = int(64 * 0.7)

                    scratch_track = MidiTrack()
                    technique_result = TechniqueRenderer.render_note_techniques(
                        note,
                        scratch_track,
                        midi_channel=assignment.midi_channel,
                        base_note=midi_note,
                        duration_ticks=duration_ticks,
                        velocity=note_velocity,
                        pitch_bend_range=pitch_bend_range,
                    )
                    techniques_rendered += technique_result.technique_count

                    if is_chord:
                        note_start = group_start_tick
                    else:
                        note_start = abs_tick
                        group_start_tick = abs_tick
                        abs_tick += duration_ticks

                    for msg in technique_result.pre_messages:
                        events.append((note_start, 0, seq, msg))
                        seq += 1
                    events.append((
                        note_start, 1, seq,
                        Message(
                            "note_on",
                            channel=assignment.midi_channel - 1,
                            note=midi_note,
                            velocity=technique_result.velocity,
                            time=0,
                        ),
                    ))
                    seq += 1
                    events.append((
                        note_start + duration_ticks, 2, seq,
                        Message(
                            "note_off",
                            channel=assignment.midi_channel - 1,
                            note=midi_note,
                            velocity=0,
                            time=0,
                        ),
                    ))
                    seq += 1
                    for msg in technique_result.post_messages:
                        events.append((note_start + duration_ticks, 3, seq, msg))
                        seq += 1

            # Sort by (abs_tick, priority, seq) and emit as MIDI delta times.
            events.sort(key=lambda e: (e[0], e[1], e[2]))
            prev_tick = 0
            for abs_t, _, _, msg in events:
                msg.time = abs_t - prev_tick
                track.append(msg)
                prev_tick = abs_t

            midi_file.tracks.append(track)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        midi_file.save(str(output_path))
        return MidiRenderResult(
            output_path=output_path,
            channel_map=ChannelMapper.to_metrics_map(assignments),
            tempo_events=tempo_result.tempo_events,
            techniques_rendered=techniques_rendered,
            warnings=render_warnings,
        )

    @staticmethod
    def _load_tree(musicxml_path: Path) -> etree._ElementTree:
        if not musicxml_path.exists():
            raise RenderValidationError(f"MusicXML input not found: {musicxml_path}")

        try:
            return etree.parse(str(musicxml_path))
        except (OSError, etree.XMLSyntaxError) as exc:
            raise RenderValidationError(f"Failed to parse MusicXML: {musicxml_path}") from exc

    @staticmethod
    def _extract_part_infos(tree: etree._ElementTree) -> list[RenderPartInfo]:
        part_names = {
            MidiRenderer._string_value(score_part.xpath("@id")): MidiRenderer._string_value(
                score_part.xpath("./*[local-name()='part-name']/text()")
            )
            for score_part in tree.xpath("//*[local-name()='part-list']/*[local-name()='score-part']")
        }
        parts: list[RenderPartInfo] = []
        for part in tree.xpath("//*[local-name()='part']"):
            part_id = MidiRenderer._string_value(part.xpath("@id"))
            part_name = part_names.get(part_id, part_id)
            role = MidiRenderer._part_role(part, part_name)
            parts.append(RenderPartInfo(part_id=part_id, part_name=part_name, role=role))
        return parts

    @staticmethod
    def _part_role(part: etree._Element, part_name: str) -> PartRole:
        role = MidiRenderer._string_value(part.xpath("@*[local-name()='role']"))
        if role in {"guitar", "bass", "drums", "other"}:
            return role  # type: ignore[return-value]

        normalized = part_name.lower()
        if "guitar" in normalized:
            return "guitar"
        if "bass" in normalized:
            return "bass"
        if "drum" in normalized or "perc" in normalized:
            return "drums"
        return "other"

    @staticmethod
    def _part_name(tree: etree._ElementTree, part_id: str) -> str:
        part_name = MidiRenderer._string_value(
            tree.xpath(
                "//*[local-name()='part-list']/*[local-name()='score-part'][@id=$part_id]/*[local-name()='part-name']/text()",
                part_id=part_id,
            )
        )
        return part_name or part_id

    @staticmethod
    def _measure_divisions(measure: etree._Element, current_divisions: int) -> int:
        divisions_text = MidiRenderer._string_value(
            measure.xpath("./*[local-name()='attributes']/*[local-name()='divisions']/text()")
        )
        if divisions_text.isdigit():
            return max(1, int(divisions_text))
        return current_divisions

    @staticmethod
    def _duration_value(note: etree._Element) -> int:
        duration_text = MidiRenderer._string_value(note.xpath("./*[local-name()='duration']/text()"))
        return int(duration_text) if duration_text.isdigit() else 1

    @staticmethod
    def _pitch_to_midi(note: etree._Element) -> int | None:
        step = MidiRenderer._string_value(note.xpath("./*[local-name()='pitch']/*[local-name()='step']/text()"))
        octave_text = MidiRenderer._string_value(note.xpath("./*[local-name()='pitch']/*[local-name()='octave']/text()"))
        alter_text = MidiRenderer._string_value(note.xpath("./*[local-name()='pitch']/*[local-name()='alter']/text()"))
        if step == "" or not octave_text.lstrip("-").isdigit():
            return None

        step_offsets = {
            "C": 0,
            "D": 2,
            "E": 4,
            "F": 5,
            "G": 7,
            "A": 9,
            "B": 11,
        }
        step_offset = step_offsets.get(step.upper())
        if step_offset is None:
            return None

        alter = int(alter_text) if alter_text.lstrip("-").isdigit() else 0
        octave = int(octave_text)
        return ((octave + 1) * 12) + step_offset + alter

    @staticmethod
    def _string_value(value: object) -> str:
        if isinstance(value, list):
            if not value:
                return ""
            return MidiRenderer._string_value(value[0])
        if value is None:
            return ""
        return str(value).strip()