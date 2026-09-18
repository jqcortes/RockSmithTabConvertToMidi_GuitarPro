"""pydantic 設定モデル。config/default.yaml をロードし、CLI オプションで上書きする。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.yaml"


class ManualRhythm(BaseModel):
    bpm: float | None = None
    offset: float | None = None
    time_signature: str | None = None


class JobConfig(BaseModel):
    quality: str = "standard"
    keep_intermediate: bool = True


class IngestConfig(BaseModel):
    target_lufs: float = -14.0


class SeparateConfig(BaseModel):
    model: str = "htdemucs_6s"
    shifts: int = 1
    overlap: float = 0.25
    device: str = "cuda"


class RhythmConfig(BaseModel):
    quantize_grid: int = 16
    allow_triplets: bool = True
    manual: ManualRhythm = ManualRhythm()


class ChordsConfig(BaseModel):
    recognizer: str = "manual"
    input: str = "mix"
    min_segment_beats: float = 1.0


class MuScriptorConfig(BaseModel):
    model: str = "medium"
    beam_size: int = 1
    batch_size: int | None = None
    instruments_guitar: list[str] = ["distorted_electric_guitar", "clean_electric_guitar", "acoustic_guitar"]
    instruments_bass: list[str] = ["electric_bass"]


class BasicPitchBassConfig(BaseModel):
    minimum_frequency: float = 30
    maximum_frequency: float = 440
    melodia_trick: bool = True


class BasicPitchConfig(BaseModel):
    onset_threshold: float = 0.5
    frame_threshold: float = 0.3
    minimum_note_length: float = 58
    multiple_pitch_bends: bool = True
    bass: BasicPitchBassConfig = BasicPitchBassConfig()


class FusionConfig(BaseModel):
    iou_threshold: float = 0.5
    run_weights: dict[str, float] = {
        "ms_mix": 1.0, "ms_gtr": 0.8, "ms_bass": 0.8, "bp_gtr": 0.5, "bp_bass": 0.5,
    }


class TranscribeConfig(BaseModel):
    muscriptor: MuScriptorConfig = MuScriptorConfig()
    basic_pitch: BasicPitchConfig = BasicPitchConfig()
    fusion: FusionConfig = FusionConfig()


class DisentangleConfig(BaseModel):
    mode: str = "rules"
    guitar_tracks: int = 2
    weights: list[float] = [1.2, 0.8, 0.9, 1.0, 1.1, 0.4, 0.7, 0.6, 1.0]
    hmm_stay_prob: float = 0.92


class ArrangeWeights(BaseModel):
    fret: float = 0.6
    open: float = 0.8
    string: float = 0.3
    span: float = 1.5
    move: float = 1.0
    str_cont: float = 0.2
    legato: float = 0.5


class ArrangeGuitarConfig(BaseModel):
    tuning: str | list[int] = "auto"
    capo: str | int = "auto"
    max_fret: int = 22
    span_max: int = 4
    weights: ArrangeWeights = ArrangeWeights()
    beam_width: int = 64
    candidates_per_group: int = 24
    preferred_fret: int = 7


class ArrangeBassConfig(BaseModel):
    tuning: str | list[int] = "auto"
    max_fret: int = 24


class ArrangeConfig(BaseModel):
    guitar: ArrangeGuitarConfig = ArrangeGuitarConfig()
    bass: ArrangeBassConfig = ArrangeBassConfig()


class TechniqueConfig(BaseModel):
    enabled: dict[str, bool] = {
        "bend": True, "vibrato": True, "slide": True, "hammer": True,
        "palm_mute": True, "dead": True, "let_ring": False, "harmonic": False,
    }
    bend_min_semitone: float = 0.7


class ExportConfig(BaseModel):
    formats: list[str] = ["gp5", "musicxml", "midi", "ascii", "check_mix"]
    gp_version: str = "5.10"


class TabForgeConfig(BaseModel):
    job: JobConfig = JobConfig()
    ingest: IngestConfig = IngestConfig()
    separate: SeparateConfig = SeparateConfig()
    rhythm: RhythmConfig = RhythmConfig()
    chords: ChordsConfig = ChordsConfig()
    transcribe: TranscribeConfig = TranscribeConfig()
    disentangle: DisentangleConfig = DisentangleConfig()
    arrange: ArrangeConfig = ArrangeConfig()
    technique: TechniqueConfig = TechniqueConfig()
    export: ExportConfig = ExportConfig()

    @classmethod
    def load(cls, path: Path | None = None, overrides: dict[str, Any] | None = None) -> TabForgeConfig:
        config_path = path or DEFAULT_CONFIG_PATH
        raw: dict[str, Any] = {}
        if config_path.exists():
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if overrides:
            raw = _deep_merge(raw, overrides)
        return cls.model_validate(raw)


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
