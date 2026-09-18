"""全 IR (中間表現) の pydantic モデル。

01_TabForge_詳細設計書.md §5 が唯一の正。フィールドを勝手に増やさない。
増やす必要があればまず設計書を直してからここを変更すること。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 5.1 grid.json
# ---------------------------------------------------------------------------


class TimeSignature(BaseModel):
    numerator: int
    denominator: int


class Beat(BaseModel):
    t: float
    beat_in_bar: int
    bar: int
    is_downbeat: bool
    conf: float = 1.0


class TempoPoint(BaseModel):
    t: float
    bpm: float


class GridIR(BaseModel):
    schema_: Literal["tabforge.grid/1"] = Field(alias="schema", default="tabforge.grid/1")
    sample_rate: int
    duration_sec: float
    tempo_bpm_global: float
    time_signature: TimeSignature
    beats: list[Beat] = Field(default_factory=list)
    tempo_map: list[TempoPoint] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# 5.2 chords.json
# ---------------------------------------------------------------------------


class ChordSegment(BaseModel):
    start: float
    end: float
    label: str
    root: int | None = None
    quality: str | None = None
    bass: int | None = None
    pitch_classes: list[int] = Field(default_factory=list)
    conf: float = 1.0


class ChordsIR(BaseModel):
    schema_: Literal["tabforge.chords/1"] = Field(alias="schema", default="tabforge.chords/1")
    source: str
    segments: list[ChordSegment] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# 5.3 notes_raw.json / notes_fused.json
# ---------------------------------------------------------------------------


class TranscriptionRun(BaseModel):
    run_id: str
    engine: str
    model: str | None = None
    input: str
    instruments: list[str] = Field(default_factory=list)


class Note(BaseModel):
    id: str
    onset: float
    offset: float
    pitch: int
    instrument: str
    conf: float = 1.0
    votes: list[str] = Field(default_factory=list)
    bend_curve: list[tuple[float, float]] | None = None
    pan: float | None = None
    src_run: str | None = None


class NotesIR(BaseModel):
    schema_: Literal["tabforge.notes/1"] = Field(alias="schema", default="tabforge.notes/1")
    runs: list[TranscriptionRun] = Field(default_factory=list)
    notes: list[Note] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# 5.4 parts.json
# ---------------------------------------------------------------------------


PartName = Literal["lead", "rhythm", "bass", "unassigned"]


class NoteFeatures(BaseModel):
    poly: float | None = None
    chord_tone: float | None = None
    on_grid: float | None = None
    register: float | None = None
    ioi: float | None = None
    pan: float | None = None
    dur: float | None = None
    periodicity: float | None = None
    cluster_width: float | None = None
    bend_extent: float | None = None


class Assignment(BaseModel):
    note_id: str
    part: PartName
    score: float
    features: NoteFeatures | None = None


class PartsIR(BaseModel):
    schema_: Literal["tabforge.parts/1"] = Field(alias="schema", default="tabforge.parts/1")
    assignments: list[Assignment] = Field(default_factory=list)
    part_stats: dict[str, int] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# 5.5 tab.json（最終中間表現）
# ---------------------------------------------------------------------------


class GpDuration(BaseModel):
    value: Literal[1, 2, 4, 8, 16, 32, 64]
    dotted: bool = False
    tuplet: tuple[int, int] | None = None  # 例: (3, 2) = 3連


class BendPoint(BaseModel):
    position: int  # 0-12
    value: int  # 1半音 = 4


class BendEffect(BaseModel):
    type: Literal["bend"] = "bend"
    points: list[tuple[int, int]] = Field(default_factory=list)


class NoteEffects(BaseModel):
    bend: BendEffect | None = None
    vibrato: bool = False
    hammer: bool = False
    slide: str | None = None
    palm_mute: bool = False
    dead: bool = False
    let_ring: bool = False
    harmonic: bool = False


class TabNote(BaseModel):
    string: int  # GP: 1 = 1弦（最高音）
    fret: int
    type: Literal["normal", "tie", "dead"] = "normal"
    effects: NoteEffects = Field(default_factory=NoteEffects)


class TabBeat(BaseModel):
    start_tick: int
    duration: GpDuration
    stroke: str | None = None
    chord: str | None = None
    notes: list[TabNote] = Field(default_factory=list)


class TabMeasure(BaseModel):
    bar: int
    time_signature: tuple[int, int]
    tempo: float
    beats: list[TabBeat] = Field(default_factory=list)


class TabTrack(BaseModel):
    name: str
    part: PartName
    tuning: list[int]  # index 0 = 1弦（最高音）
    capo: int = 0
    string_count: int
    midi_program: int = 30
    measures: list[TabMeasure] = Field(default_factory=list)


class TabQuality(BaseModel):
    note_count: int = 0
    unplayable_dropped: int = 0
    position_jumps_gt5: int = 0


class TabIR(BaseModel):
    schema_: Literal["tabforge.tab/1"] = Field(alias="schema", default="tabforge.tab/1")
    tracks: list[TabTrack] = Field(default_factory=list)
    quality: TabQuality = Field(default_factory=TabQuality)

    model_config = {"populate_by_name": True}
