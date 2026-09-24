"""T5-2 相当: `tabforge batch` が1曲の失敗で他曲を止めないことを確認する。"""
from __future__ import annotations

import numpy as np
import soundfile as sf
from typer.testing import CliRunner

from tabforge.cli import app

runner = CliRunner()


def test_batch_continues_after_one_file_fails(tmp_path):
    audio_dir = tmp_path / "songs"
    audio_dir.mkdir()

    # 正常な音源(pyloudnorm の block size 要件を満たすため 1秒以上にする)
    t = np.linspace(0, 1.0, int(44100 * 1.0), endpoint=False)
    tone = (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    sf.write(audio_dir / "good.wav", np.stack([tone, tone], axis=1), 44100)

    # 壊れた「音源」(実際はテキスト) -> S0 Ingest で失敗するはず
    (audio_dir / "broken.wav").write_text("not a real wav file", encoding="utf-8")

    out_dir = tmp_path / "out"
    result = runner.invoke(app, [
        "batch", str(audio_dir), "--out-dir", str(out_dir),
        "--pattern", "*.wav",
    ])

    assert result.exit_code == 0, result.output
    assert "batch complete: 1/2 succeeded" in result.output
    assert "Failures" in result.output
    assert "broken.wav" in result.output
    assert "good.wav" in result.output
