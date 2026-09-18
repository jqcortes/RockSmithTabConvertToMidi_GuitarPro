"""音声 I/O ユーティリティ。ffmpeg 呼び出し・LUFS 正規化・無音トリム。"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

TARGET_SAMPLE_RATE = 44100


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def to_wav_stereo(src: Path, dst: Path, sample_rate: int = TARGET_SAMPLE_RATE) -> None:
    """ffmpeg で 44100Hz / 2ch / float32 wav に統一する。

    ffmpeg が無い環境向けに soundfile + numpy によるフォールバックも用意する
    （リサンプルはしないため、フォールバック時は入力が既に対象サンプルレート
    であることを前提とする）。
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if ffmpeg_available():
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src),
                "-ar", str(sample_rate), "-ac", "2", "-sample_fmt", "flt",
                str(dst),
            ],
            check=True,
            capture_output=True,
        )
        return

    data, sr = sf.read(src, always_2d=True, dtype="float32")
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    elif data.shape[1] > 2:
        data = data[:, :2]
    if sr != sample_rate:
        raise RuntimeError(
            f"ffmpeg が見つからず、リサンプルできません ({sr}Hz -> {sample_rate}Hz)。"
            " ffmpeg をインストールするか、あらかじめ 44.1kHz の音源を用意してください。"
        )
    sf.write(dst, data, sample_rate, subtype="FLOAT")


def to_mono(src: Path, dst: Path) -> None:
    data, sr = sf.read(src, always_2d=True, dtype="float32")
    mono = data.mean(axis=1)
    dst.parent.mkdir(parents=True, exist_ok=True)
    sf.write(dst, mono, sr, subtype="FLOAT")


def normalize_lufs(src: Path, dst: Path, target_lufs: float) -> None:
    """pyloudnorm で LUFS 正規化する（ピーク -1dBFS でクリップ保護）。"""
    import pyloudnorm as pyln

    data, sr = sf.read(src, dtype="float32")
    meter = pyln.Meter(sr)
    loudness = meter.integrated_loudness(data)
    normalized = pyln.normalize.loudness(data, loudness, target_lufs)
    peak = np.max(np.abs(normalized)) if normalized.size else 0.0
    if peak > 0.891:  # -1dBFS
        normalized = normalized * (0.891 / peak)
    dst.parent.mkdir(parents=True, exist_ok=True)
    sf.write(dst, normalized, sr, subtype="FLOAT")


def trim_silence(src: Path, dst: Path, threshold_db: float = -60.0, margin_sec: float = 0.5) -> None:
    """冒頭/末尾の無音をトリムする（margin_sec は残す余白）。"""
    data, sr = sf.read(src, always_2d=True, dtype="float32")
    envelope = np.max(np.abs(data), axis=1)
    threshold = 10 ** (threshold_db / 20.0)
    above = np.where(envelope > threshold)[0]
    if above.size == 0:
        sf.write(dst, data, sr, subtype="FLOAT")
        return
    margin = int(margin_sec * sr)
    start = max(0, above[0] - margin)
    end = min(len(data), above[-1] + margin)
    dst.parent.mkdir(parents=True, exist_ok=True)
    sf.write(dst, data[start:end], sr, subtype="FLOAT")
