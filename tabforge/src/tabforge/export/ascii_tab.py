"""ASCII タブ（差分レビュー用のプレーンタブ）。設計書 §10.2、実装指示書 T4-3。"""
from __future__ import annotations

from pathlib import Path

from tabforge.ir.models import TabIR, TabTrack

_STANDARD_6_LABELS = ["e", "B", "G", "D", "A", "E"]


def _string_labels(track: TabTrack) -> list[str]:
    if len(track.tuning) == 6:
        return _STANDARD_6_LABELS
    return [str(p) for p in track.tuning]


def render_track(track: TabTrack) -> str:
    n_strings = len(track.tuning)
    rows: list[list[str]] = [[] for _ in range(n_strings)]

    for measure in track.measures:
        if not measure.beats:
            for row in rows:
                row.append("----")
        for beat in measure.beats:
            frets_by_string = {n.string: n.fret for n in beat.notes}
            for s in range(1, n_strings + 1):
                cell = str(frets_by_string[s]) if s in frets_by_string else "-"
                rows[s - 1].append(cell.rjust(2, "-"))
        for row in rows:
            row.append("|")

    labels = _string_labels(track)
    lines = [f"=== {track.name} (tuning={list(track.tuning)}) ==="]
    for label, row in zip(labels, rows, strict=True):
        lines.append(f"{label}|" + "-".join(row))
    return "\n".join(lines)


def render_ascii_tab(tab: TabIR) -> str:
    return "\n\n".join(render_track(track) for track in tab.tracks)


def write_ascii_tab(tab: TabIR, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_ascii_tab(tab), encoding="utf-8")
