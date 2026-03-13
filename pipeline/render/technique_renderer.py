"""Guitar technique to MIDI message conversion for the Render domain."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree
from mido import Message, MidiTrack


@dataclass(frozen=True)
class TechniqueRenderResult:
    """Technique rendering side effects for a single note."""

    velocity: int
    duration_ticks: int
    technique_count: int
    pre_messages: list[Message]
    post_messages: list[Message]


class TechniqueRenderer:
    """Translate supported guitar notations into MIDI control messages."""

    @staticmethod
    def render_note_techniques(
        note: etree._Element,
        track: MidiTrack,
        *,
        midi_channel: int,
        base_note: int,
        duration_ticks: int,
        velocity: int,
        pitch_bend_range: int = 2,
    ) -> TechniqueRenderResult:
        """Render supported techniques for a single note and return note adjustments."""
        del base_note

        pre_messages: list[Message] = []
        post_messages: list[Message] = []
        technique_count = 0
        adjusted_velocity = velocity
        adjusted_duration = duration_ticks
        channel = midi_channel - 1

        technical = note.xpath("./*[local-name()='notations']/*[local-name()='technical']")
        if technical:
            bend_alter = _first_text(
                technical[0].xpath("./*[local-name()='bend']/*[local-name()='bend-alter']/text()")
            )
            if bend_alter != "" and _is_number(bend_alter):
                pitch_delta = _pitchwheel_value(float(bend_alter), pitch_bend_range)
                pre_messages.append(Message("pitchwheel", channel=channel, pitch=pitch_delta, time=0))
                post_messages.append(Message("pitchwheel", channel=channel, pitch=0, time=0))
                technique_count += 1

            if technical[0].xpath("./*[local-name()='slide']"):
                pre_messages.append(Message("pitchwheel", channel=channel, pitch=2048, time=0))
                post_messages.append(Message("pitchwheel", channel=channel, pitch=0, time=0))
                technique_count += 1

            if technical[0].xpath("./*[local-name()='palm-mute']"):
                pre_messages.append(Message("control_change", channel=channel, control=11, value=40, time=0))
                post_messages.append(Message("control_change", channel=channel, control=11, value=127, time=0))
                adjusted_duration = max(1, duration_ticks // 2)
                technique_count += 1

            if technical[0].xpath("./*[local-name()='hammer-on']"):
                adjusted_velocity = int(adjusted_velocity * 0.7)
                technique_count += 1

            if technical[0].xpath("./*[local-name()='pull-off']"):
                adjusted_velocity = int(adjusted_velocity * 0.6)
                technique_count += 1

        for message in pre_messages:
            track.append(message)
        for message in post_messages:
            track.append(message)

        return TechniqueRenderResult(
            velocity=adjusted_velocity,
            duration_ticks=adjusted_duration,
            technique_count=technique_count,
            pre_messages=pre_messages,
            post_messages=post_messages,
        )


def _first_text(values: list[object]) -> str:
    if not values:
        return ""
    return str(values[0]).strip()


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _pitchwheel_value(semitones: float, pitch_bend_range: int) -> int:
    bounded_range = max(1, pitch_bend_range)
    bounded = max(float(-bounded_range), min(float(bounded_range), semitones))
    return max(-8191, min(8191, int((bounded / float(bounded_range)) * 8191)))