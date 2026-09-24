"""report.html 生成（設計書 §10.4）。

- 総ノート数 / パート別内訳 / unassigned 件数
- 推定チューニング・拍子・BPM（S7 で確定済みの値を tab.json から引用）
- 警告一覧（ビート不安定区間、position jump 多発、未割当ノート超過）
- 小節ごとの conf 平均（低い小節 = 人手確認優先箇所）

パート別ピアノロール／タブ位置ヒートマップ（設計書が挙げる可視化）は
このバージョンでは実装しない（別途 P5 のレビュー UI で対応する想定）。
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

from tabforge.ir.models import GridIR, Note, NotesIR, PartsIR, TabIR

UNASSIGNED_WARNING_THRESHOLD = 0.05
WORST_BARS_SHOWN = 10


@dataclass
class ReportContext:
    total_notes: int
    part_stats: dict[str, int]
    tempo_bpm: float
    time_signature: str
    tracks: list[dict]
    warnings: list[str]
    worst_bars: list[tuple[int, float]]  # (bar, avg_conf) 昇順


def _bar_for_time(t: float, grid: GridIR) -> int:
    if not grid.beats:
        return 1
    bar = 1
    for beat in grid.beats:
        if beat.t <= t:
            bar = beat.bar
        else:
            break
    return bar


def _bar_confidences(notes: list[Note], grid: GridIR) -> dict[int, list[float]]:
    by_bar: dict[int, list[float]] = {}
    for note in notes:
        bar = _bar_for_time(note.onset, grid)
        by_bar.setdefault(bar, []).append(note.conf)
    return by_bar


def build_report_context(notes_ir: NotesIR, parts: PartsIR, grid: GridIR, tab: TabIR) -> ReportContext:
    total_notes = len(notes_ir.notes)
    part_stats = dict(parts.part_stats)

    warnings: list[str] = list(grid.warnings)

    unassigned = part_stats.get("unassigned", 0)
    if total_notes and unassigned / total_notes > UNASSIGNED_WARNING_THRESHOLD:
        warnings.append(
            f"unassigned が {unassigned}/{total_notes} 件 "
            f"({unassigned / total_notes:.1%}) で閾値 {UNASSIGNED_WARNING_THRESHOLD:.0%} を超過。"
        )
    if tab.quality.position_jumps_gt5 > 0:
        warnings.append(f"5フレット超のポジション移動が {tab.quality.position_jumps_gt5} 回検出された。")
    if tab.quality.unplayable_dropped > 0:
        warnings.append(f"範囲外・演奏不可能と判定され破棄されたノート群が {tab.quality.unplayable_dropped} 件ある。")

    tracks = [
        {
            "name": track.name,
            "part": track.part,
            "tuning": list(track.tuning),
            "string_count": track.string_count,
            "measure_count": len(track.measures),
            "beat_count": sum(len(m.beats) for m in track.measures),
        }
        for track in tab.tracks
    ]

    by_bar = _bar_confidences(notes_ir.notes, grid)
    bar_avg = sorted(
        ((bar, sum(confs) / len(confs)) for bar, confs in by_bar.items() if confs),
        key=lambda item: item[1],
    )[:WORST_BARS_SHOWN]

    return ReportContext(
        total_notes=total_notes,
        part_stats=part_stats,
        tempo_bpm=grid.tempo_bpm_global,
        time_signature=f"{grid.time_signature.numerator}/{grid.time_signature.denominator}",
        tracks=tracks,
        warnings=warnings,
        worst_bars=bar_avg,
    )


def _esc(text: str) -> str:
    return html.escape(str(text))


def render_report_html(ctx: ReportContext) -> str:
    part_rows = "".join(
        f"<tr><td>{_esc(part)}</td><td>{count}</td></tr>"
        for part, count in sorted(ctx.part_stats.items())
    )
    track_rows = "".join(
        f"<tr><td>{_esc(t['name'])}</td><td>{_esc(t['part'])}</td>"
        f"<td>{_esc(t['tuning'])}</td><td>{t['string_count']}</td>"
        f"<td>{t['measure_count']}</td><td>{t['beat_count']}</td></tr>"
        for t in ctx.tracks
    )
    warning_items = "".join(f"<li>{_esc(w)}</li>" for w in ctx.warnings) or "<li>(警告なし)</li>"
    bar_rows = "".join(
        f"<tr><td>{bar}</td><td>{conf:.2f}</td></tr>" for bar, conf in ctx.worst_bars
    ) or "<tr><td colspan='2'>(データなし)</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>TabForge Report</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 880px; margin: 2rem auto; color: #222; }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; border-bottom: 1px solid #ddd; padding-bottom: .25rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: .5rem; }}
  th, td {{ border: 1px solid #ddd; padding: .4rem .6rem; text-align: left; font-size: .9rem; }}
  th {{ background: #f5f5f5; }}
  .stat {{ display: inline-block; margin-right: 2rem; }}
  .stat b {{ font-size: 1.2rem; }}
  ul {{ padding-left: 1.2rem; }}
</style>
</head>
<body>
<h1>TabForge Report</h1>

<h2>サマリ</h2>
<div class="stat">総ノート数<br><b>{ctx.total_notes}</b></div>
<div class="stat">推定 BPM<br><b>{ctx.tempo_bpm:.1f}</b></div>
<div class="stat">拍子<br><b>{_esc(ctx.time_signature)}</b></div>

<h2>パート別内訳</h2>
<table><tr><th>パート</th><th>ノート数</th></tr>{part_rows}</table>

<h2>トラック</h2>
<table>
<tr><th>名前</th><th>パート</th><th>チューニング</th><th>弦数</th><th>小節数</th><th>拍数</th></tr>
{track_rows}
</table>

<h2>警告</h2>
<ul>{warning_items}</ul>

<h2>要確認小節（採譜信頼度が低い順・上位{WORST_BARS_SHOWN}件）</h2>
<table><tr><th>小節</th><th>平均 conf</th></tr>{bar_rows}</table>

</body>
</html>
"""


def write_report(notes_ir: NotesIR, parts: PartsIR, grid: GridIR, tab: TabIR, out: Path) -> None:
    ctx = build_report_context(notes_ir, parts, grid, tab)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report_html(ctx), encoding="utf-8")
