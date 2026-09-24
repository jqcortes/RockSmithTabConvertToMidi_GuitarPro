"""検証用 MIDI 出力（設計書 §1.2 `score.mid`）。

`export.musicxml_writer.build_score` と同じ music21 Score を再利用し、
タブ譜と実質同一のノート内容（テンポ含む）を MIDI Type 1 として書き出す。
"""
from __future__ import annotations

from pathlib import Path

from tabforge.export.musicxml_writer import build_score
from tabforge.ir.models import TabIR


def write_midi(tab: TabIR, out: Path) -> None:
    score = build_score(tab)
    out.parent.mkdir(parents=True, exist_ok=True)
    score.write("midi", fp=str(out))
