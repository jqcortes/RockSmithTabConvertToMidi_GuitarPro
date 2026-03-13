"""Role-based MIDI channel assignment for the Render domain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from pipeline.render.errors import RenderExecutionError

PartRole = Literal["guitar", "bass", "drums", "other"]
_DEFAULT_OTHER_PROGRAM = 1
_RESERVED_CHANNELS = {10}
_FIXED_ASSIGNMENTS: dict[PartRole, tuple[int, int | None]] = {
    "guitar": (1, 29),
    "bass": (2, 33),
    "drums": (10, None),
    "other": (0, _DEFAULT_OTHER_PROGRAM),
}


@dataclass(frozen=True)
class RenderPartInfo:
    """Minimal part metadata needed for Render channel assignment."""

    part_id: str
    part_name: str
    role: PartRole


@dataclass(frozen=True)
class ChannelAssignment:
    """Resolved MIDI channel/program for a part."""

    part_id: str
    role: PartRole
    midi_channel: int
    midi_program: int | None


class ChannelMapper:
    """Assign MIDI channels and GM programs from logical part roles."""

    @staticmethod
    def assign(parts: Sequence[RenderPartInfo]) -> list[ChannelAssignment]:
        """Assign fixed channels for known roles and sequential channels for others."""
        assignments: list[ChannelAssignment] = []
        used_other_channels: set[int] = set()

        for part in parts:
            midi_program: int | None
            if part.role == "other":
                midi_channel = ChannelMapper._next_available_other_channel(used_other_channels)
                used_other_channels.add(midi_channel)
                midi_program = _DEFAULT_OTHER_PROGRAM
            else:
                midi_channel, midi_program = _FIXED_ASSIGNMENTS[part.role]
            assignments.append(
                ChannelAssignment(
                    part_id=part.part_id,
                    role=part.role,
                    midi_channel=midi_channel,
                    midi_program=midi_program,
                )
            )

        return assignments

    @staticmethod
    def to_metrics_map(assignments: Sequence[ChannelAssignment]) -> dict[str, str]:
        """Serialize assignments into StepResult metrics-friendly strings."""
        return {
            assignment.part_id: (
                f"channel={assignment.midi_channel},"
                f"program={assignment.midi_program if assignment.midi_program is not None else 'none'},"
                f"role={assignment.role}"
            )
            for assignment in assignments
        }

    @staticmethod
    def _next_available_other_channel(used_other_channels: set[int]) -> int:
        for midi_channel in range(1, 17):
            if midi_channel in _RESERVED_CHANNELS or midi_channel in used_other_channels:
                continue
            if midi_channel in {channel for channel, _ in _FIXED_ASSIGNMENTS.values() if channel != 0}:
                continue
            return midi_channel
        raise RenderExecutionError("No MIDI channels available for additional parts")