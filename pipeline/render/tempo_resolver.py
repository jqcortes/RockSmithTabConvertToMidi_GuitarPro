"""Meta track and tempo extraction for the Render domain."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lxml import etree
from mido import MetaMessage, MidiTrack, bpm2tempo

from pipeline.render.errors import RenderValidationError

_DEFAULT_BPM = 120
_FIFTHS_TO_KEY = {
    -7: "Cb",
    -6: "Gb",
    -5: "Db",
    -4: "Ab",
    -3: "Eb",
    -2: "Bb",
    -1: "F",
    0: "C",
    1: "G",
    2: "D",
    3: "A",
    4: "E",
    5: "B",
    6: "F#",
    7: "C#",
}


@dataclass(frozen=True)
class TempoResolution:
    """Resolved meta track and related metadata."""

    track: MidiTrack
    tempo_events: int
    warnings: list[str]


class TempoResolver:
    """Build MIDI meta track from MusicXML tempo and score metadata."""

    @staticmethod
    def build_meta_track(source: Path | etree._ElementTree, *, default_bpm: int = _DEFAULT_BPM) -> TempoResolution:
        """Build Track 0 metadata from a MusicXML path or parsed tree."""
        tree = TempoResolver._load_tree(source)
        track = MidiTrack()
        track.append(MetaMessage("track_name", name="Meta", time=0))

        warnings: list[str] = []
        tempo_values = TempoResolver._tempo_values(tree)
        if not tempo_values:
            tempo_values = [default_bpm]
            warnings.append(f"Default tempo applied: {default_bpm} BPM")

        for bpm in tempo_values:
            track.append(MetaMessage("set_tempo", tempo=bpm2tempo(bpm), time=0))

        numerator, denominator = TempoResolver._time_signature(tree)
        track.append(
            MetaMessage(
                "time_signature",
                numerator=numerator,
                denominator=denominator,
                clocks_per_click=24,
                notated_32nd_notes_per_beat=8,
                time=0,
            )
        )

        track.append(MetaMessage("key_signature", key=TempoResolver._key_signature(tree), time=0))
        return TempoResolution(track=track, tempo_events=len(tempo_values), warnings=warnings)

    @staticmethod
    def _load_tree(source: Path | etree._ElementTree) -> etree._ElementTree:
        if isinstance(source, etree._ElementTree):
            return source

        if not source.exists():
            raise RenderValidationError(f"MusicXML input not found: {source}")

        try:
            return etree.parse(str(source))
        except (OSError, etree.XMLSyntaxError) as exc:
            raise RenderValidationError(f"Failed to parse MusicXML: {source}") from exc

    @staticmethod
    def _tempo_values(tree: etree._ElementTree) -> list[int]:
        sound_tempos = [
            int(float(value))
            for value in tree.xpath("//*[local-name()='sound']/@tempo")
            if _is_number(str(value))
        ]
        if sound_tempos:
            return sound_tempos

        metronome_tempos = [
            int(float(value))
            for value in tree.xpath(
                "//*[local-name()='direction-type']/*[local-name()='metronome']/*[local-name()='per-minute']/text()"
            )
            if _is_number(str(value))
        ]
        return metronome_tempos

    @staticmethod
    def _time_signature(tree: etree._ElementTree) -> tuple[int, int]:
        beats = _first_text(tree.xpath("//*[local-name()='time']/*[local-name()='beats']/text()"), default="4")
        beat_type = _first_text(tree.xpath("//*[local-name()='time']/*[local-name()='beat-type']/text()"), default="4")
        numerator = int(beats) if beats.isdigit() else 4
        denominator = int(beat_type) if beat_type.isdigit() else 4
        return numerator, denominator

    @staticmethod
    def _key_signature(tree: etree._ElementTree) -> str:
        fifths_text = _first_text(tree.xpath("//*[local-name()='key']/*[local-name()='fifths']/text()"), default="0")
        fifths = int(fifths_text) if fifths_text.lstrip("-").isdigit() else 0
        return _FIFTHS_TO_KEY.get(fifths, "C")


def _first_text(values: list[object], *, default: str) -> str:
    if not values:
        return default
    return str(values[0]).strip() or default


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True