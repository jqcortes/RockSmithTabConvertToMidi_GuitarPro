"""check_mix.wav 生成（設計書 §10.3）。

MuScriptor の `--auralize` と同じ思想: L=原曲、R=生成タブの合成音を配置した
ステレオ wav。ヘッドホンで左右を聴き比べるだけで誤採譜箇所が即座に分かる。

fluidsynth + SoundFont は依存として重く、この実行環境では検証もできないため、
シンプルな減衰サイン波の加算合成で代替する（音色は簡素だが、オンセット・
ピッチ・リズムの妥当性を耳で確認する目的には十分）。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from tabforge.ir.models import TabIR, TabTrack
from tabforge.stages.s6_quantize import PPQ
from tabforge.theory.duration import duration_ticks

DECAY_RATE = 3.0  # 大きいほど早く減衰する
AMPLITUDE = 0.2


def _midi_to_hz(pitch: int) -> float:
    return 440.0 * 2 ** ((pitch - 69) / 12.0)


def _track_events(track: TabTrack) -> list[tuple[float, float, int]]:
    """(onset_sec, duration_sec, midi_pitch) のリストを返す。"""
    events: list[tuple[float, float, int]] = []
    cursor = 0.0
    for measure in track.measures:
        bpm = measure.tempo if measure.tempo > 0 else 120.0
        beat_len = 60.0 / bpm
        if not measure.beats:
            numerator, denominator = measure.time_signature
            cursor += numerator * (4.0 / denominator) * beat_len
            continue
        for beat in measure.beats:
            d = beat.duration
            dur_sec = (duration_ticks(d.value, PPQ, d.dotted, d.tuplet) / PPQ) * beat_len
            for note in beat.notes:
                pitch = track.tuning[note.string - 1] + note.fret
                events.append((cursor, dur_sec, pitch))
            cursor += dur_sec
    return events


def synthesize(tab: TabIR, sample_rate: int = 44100) -> np.ndarray:
    """全トラックを減衰サイン波で加算合成したモノラル信号を返す。"""
    all_events: list[tuple[float, float, int]] = []
    max_end = 0.0
    for track in tab.tracks:
        for onset, dur, pitch in _track_events(track):
            all_events.append((onset, dur, pitch))
            max_end = max(max_end, onset + dur)

    n_samples = max(1, int(max_end * sample_rate) + 1)
    signal = np.zeros(n_samples, dtype=np.float32)
    for onset, dur, pitch in all_events:
        if dur <= 0:
            continue
        start = int(onset * sample_rate)
        length = max(1, int(dur * sample_rate))
        t = np.arange(length) / sample_rate
        freq = _midi_to_hz(pitch)
        envelope = np.exp(-DECAY_RATE * t / dur)
        tone = AMPLITUDE * np.sin(2 * np.pi * freq * t) * envelope
        end = min(n_samples, start + length)
        if end > start:
            signal[start:end] += tone[: end - start]

    peak = float(np.max(np.abs(signal))) if signal.size else 0.0
    if peak > 0.9:
        signal = signal * (0.9 / peak)
    return signal


def write_check_mix(tab: TabIR, mix_wav: Path, out: Path, sample_rate: int = 44100) -> None:
    synth = synthesize(tab, sample_rate)

    orig, sr = sf.read(str(mix_wav), always_2d=True, dtype="float32")
    orig_mono = orig.mean(axis=1)
    if sr != sample_rate:
        # サンプルレート不一致は S0 Ingest が 44.1kHz に統一している前提のため
        # ここでのリサンプルは行わず、長さだけ合わせて警告なく進める。
        pass

    n = max(len(orig_mono), len(synth))
    left = np.zeros(n, dtype=np.float32)
    left[: len(orig_mono)] = orig_mono
    right = np.zeros(n, dtype=np.float32)
    right[: len(synth)] = synth

    stereo = np.stack([left, right], axis=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), stereo, sample_rate, subtype="FLOAT")
