"""S4 Note Transcription（設計書 §7.1、実装指示書 T1-4 / T2-2）。

ベース (ms_mix, ms_bass, bp_bass) + ギター (ms_gtr, bp_gtr) の5ランを実行する。
`ms_gtr` は Demucs のアーティファクトで誤検出が増えうるため、S4b 融合側の
`run_weights` を控えめにし、`bp_gtr` 単独ノートは破棄する規則を守る（§7.2 Step3）。

MuScriptor / Basic Pitch のいずれかが未インストールの場合はそのランだけを
degraded でスキップし、警告を記録して継続する（R1/R4: 段ごとに失敗を封じ込める）。
"""
from __future__ import annotations

from dataclasses import dataclass

from tabforge.config import TabForgeConfig
from tabforge.engines.basic_pitch_adapter import BasicPitchEngine, BasicPitchUnavailable
from tabforge.engines.muscriptor_adapter import MuScriptorEngine, MuScriptorUnavailable
from tabforge.instruments import Instruments
from tabforge.ir import io as ir_io
from tabforge.ir.models import Note, NotesIR, TranscriptionRun
from tabforge.job import Job


@dataclass
class Stage:
    name: str = "s4_transcribe"

    def is_done(self, job: Job) -> bool:
        return job.stage_output(self.name).exists()

    def run(self, job: Job, cfg: TabForgeConfig) -> None:
        mus_cfg = cfg.transcribe.muscriptor
        bp_cfg = cfg.transcribe.basic_pitch

        instruments = Instruments.load()
        if not instruments.verified:
            job.logger.warning(
                self.name,
                "config/instruments.yaml が未実測 (verified=false)。"
                " scripts/probe_muscriptor.py を実行して実測値を確定させること。",
            )

        mix_mono = job.audio_dir / "mix_mono.wav"
        bass_stem = job.stems_dir / "bass.wav"
        bass_source = bass_stem if bass_stem.exists() else job.stems_dir / "mix.wav"
        guitar_stem = job.stems_dir / "guitar.wav"
        guitar_source = guitar_stem if guitar_stem.exists() else job.stems_dir / "mix.wav"

        runs: list[TranscriptionRun] = []
        notes: list[Note] = []

        # ms_mix: フルミックス + ギター/ベース同時条件付け（設計書 D2）
        try:
            engine = MuScriptorEngine(
                model=mus_cfg.model, beam_size=mus_cfg.beam_size,
                batch_size=mus_cfg.batch_size, device="cpu",
            )
            all_instruments = mus_cfg.instruments_guitar + mus_cfg.instruments_bass
            run_notes = engine.transcribe(mix_mono, all_instruments, run_id="ms_mix")
            notes.extend(run_notes)
            runs.append(
                TranscriptionRun(
                    run_id="ms_mix", engine="muscriptor", model=mus_cfg.model,
                    input=str(mix_mono), instruments=all_instruments,
                )
            )
        except MuScriptorUnavailable as exc:
            job.logger.warning(self.name, f"ms_mix degraded: {exc}")

        # ms_bass: ベースステム単独
        try:
            engine = MuScriptorEngine(
                model=mus_cfg.model, beam_size=mus_cfg.beam_size,
                batch_size=mus_cfg.batch_size, device="cpu",
            )
            run_notes = engine.transcribe(bass_source, mus_cfg.instruments_bass, run_id="ms_bass")
            notes.extend(run_notes)
            runs.append(
                TranscriptionRun(
                    run_id="ms_bass", engine="muscriptor", model=mus_cfg.model,
                    input=str(bass_source), instruments=mus_cfg.instruments_bass,
                )
            )
        except MuScriptorUnavailable as exc:
            job.logger.warning(self.name, f"ms_bass degraded: {exc}")

        # ms_gtr: ギターステム単独（埋もれたギターの回収。設計書 §7.1）
        try:
            engine = MuScriptorEngine(
                model=mus_cfg.model, beam_size=mus_cfg.beam_size,
                batch_size=mus_cfg.batch_size, device="cpu",
            )
            run_notes = engine.transcribe(guitar_source, mus_cfg.instruments_guitar, run_id="ms_gtr")
            notes.extend(run_notes)
            runs.append(
                TranscriptionRun(
                    run_id="ms_gtr", engine="muscriptor", model=mus_cfg.model,
                    input=str(guitar_source), instruments=mus_cfg.instruments_guitar,
                )
            )
        except MuScriptorUnavailable as exc:
            job.logger.warning(self.name, f"ms_gtr degraded: {exc}")

        # bp_gtr: Basic Pitch によるベンド曲線とオンセット精緻化
        try:
            bp_engine = BasicPitchEngine(
                onset_threshold=bp_cfg.onset_threshold,
                frame_threshold=bp_cfg.frame_threshold,
                minimum_note_length=bp_cfg.minimum_note_length,
                multiple_pitch_bends=bp_cfg.multiple_pitch_bends,
            )
            instrument_name = mus_cfg.instruments_guitar[0] if mus_cfg.instruments_guitar else "distorted_electric_guitar"
            run_notes = bp_engine.transcribe(guitar_source, instrument=instrument_name, run_id="bp_gtr")
            notes.extend(run_notes)
            runs.append(
                TranscriptionRun(
                    run_id="bp_gtr", engine="basic_pitch", input=str(guitar_source),
                    instruments=[instrument_name],
                )
            )
        except BasicPitchUnavailable as exc:
            job.logger.warning(self.name, f"bp_gtr degraded: {exc}")

        # bp_bass: Basic Pitch によるベース補完
        try:
            bp_engine = BasicPitchEngine(
                onset_threshold=bp_cfg.onset_threshold,
                frame_threshold=bp_cfg.frame_threshold,
                minimum_note_length=bp_cfg.minimum_note_length,
                multiple_pitch_bends=bp_cfg.multiple_pitch_bends,
                minimum_frequency=bp_cfg.bass.minimum_frequency,
                maximum_frequency=bp_cfg.bass.maximum_frequency,
                melodia_trick=bp_cfg.bass.melodia_trick,
            )
            instrument_name = mus_cfg.instruments_bass[0] if mus_cfg.instruments_bass else "electric_bass"
            run_notes = bp_engine.transcribe(bass_source, instrument=instrument_name, run_id="bp_bass")
            notes.extend(run_notes)
            runs.append(
                TranscriptionRun(
                    run_id="bp_bass", engine="basic_pitch", input=str(bass_source),
                    instruments=[instrument_name],
                )
            )
        except BasicPitchUnavailable as exc:
            job.logger.warning(self.name, f"bp_bass degraded: {exc}")

        if not runs:
            job.logger.warning(
                self.name,
                "全ての採譜エンジンが利用不可のため notes_raw は空になる。"
                " `pip install -e '.[ml]'` 後に --force s4_transcribe で再実行すること。",
            )

        notes_ir = NotesIR(runs=runs, notes=notes)
        ir_io.save(notes_ir, job.stage_output(self.name))
