"""TabForge CLI（typer エントリポイント）。02_TabForge_実装指示書.md T0-5 準拠。"""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import NotesIR, PartsIR, TabIR
from tabforge.job import STAGE_ORDER, Job, job_id_from_audio

app = typer.Typer(add_completion=False, help="原曲音源 → ギター/ベース GuitarPro タブ譜 自動生成")
console = Console()


def _build_stages(cfg: TabForgeConfig | None = None):
    # 遅延 import: CLI 起動時に重量級依存 (torch 等) を要求しないようにする。
    from tabforge.stages import (
        s0_ingest,
        s1_separate,
        s2_rhythm,
        s3_chords,
        s4_transcribe,
        s4b_fuse,
        s5_disentangle,
        s6_quantize,
        s7_arrange,
        s9_export,
    )

    formats = cfg.export.formats if cfg is not None else ["gp5"]
    return [
        s0_ingest.Stage(),
        s1_separate.Stage(),
        s2_rhythm.Stage(),
        s3_chords.Stage(),
        s4_transcribe.Stage(),
        s4b_fuse.Stage(),
        s5_disentangle.Stage(),
        s6_quantize.Stage(),
        s7_arrange.Stage(),
        s9_export.Stage(formats=formats),
    ]


def _resolve_job_dir(audio: Path, out_dir: Path) -> Path:
    job_id = job_id_from_audio(audio)
    return out_dir / job_id


@app.command()
def run(
    audio: Path = typer.Argument(..., exists=True, help="入力音源 (wav/mp3/flac 等)"),
    out_dir: Path = typer.Option(Path("out"), "--out-dir", help="ジョブ出力先の親ディレクトリ"),
    config: Path | None = typer.Option(None, "--config", help="設定ファイル (yaml)"),
    from_stage: str | None = typer.Option(None, "--from", help=f"開始ステージ ({', '.join(STAGE_ORDER)})"),
    to_stage: str | None = typer.Option(None, "--to", help="終了ステージ"),
    force: list[str] = typer.Option([], "--force", help="指定ステージのキャッシュを破棄して再計算"),
    bpm: float | None = typer.Option(None, help="S2 をバイパスして固定 BPM を使う"),
    offset: float | None = typer.Option(None, help="固定 BPM 使用時の先頭オフセット(秒)"),
    time_sig: str | None = typer.Option(None, "--time-sig", help="例: 4/4"),
    guitar_tracks: int = typer.Option(2, "--guitar-tracks", help="1|2|3"),
    tuning: str | None = typer.Option(None, help='"E-standard"|"drop-d"|"eb-standard"|"40,45,50,55,59,64"'),
    quality: str = typer.Option("standard", help="fast|standard|high"),
    no_separate: bool = typer.Option(False, "--no-separate", help="Demucs を使わず mix 推論のみ"),
) -> None:
    """全段実行、または --from/--to で部分再実行する。"""
    overrides: dict = {"job": {"quality": quality}}
    if bpm is not None or offset is not None or time_sig is not None:
        overrides.setdefault("rhythm", {})["manual"] = {
            "bpm": bpm, "offset": offset, "time_signature": time_sig,
        }
    if no_separate:
        overrides.setdefault("separate", {})["model"] = "none"
    overrides.setdefault("disentangle", {})["guitar_tracks"] = guitar_tracks
    if tuning is not None:
        overrides.setdefault("arrange", {}).setdefault("guitar", {})["tuning"] = tuning

    cfg = TabForgeConfig.load(path=config, overrides=overrides)

    job_dir = _resolve_job_dir(audio, out_dir)
    job = Job(job_dir=job_dir, source_audio=audio)

    stages = _build_stages(cfg)
    known = {s.name for s in stages}
    for name in [from_stage, to_stage, *force]:
        if name is not None and name not in known:
            raise typer.BadParameter(f"unknown stage: {name!r}. choices={sorted(known)}")

    job.run_pipeline(
        stages, cfg, from_stage=from_stage, to_stage=to_stage, force_stages=set(force),
    )
    console.print(f"[green]done[/green] job_dir={job_dir}")


@app.command()
def inspect(job_dir: Path = typer.Argument(..., exists=True, file_okay=False)) -> None:
    """IR のサマリ表示。"""
    job = Job(job_dir=job_dir)
    table = Table(title=f"tabforge inspect: {job_dir}")
    table.add_column("stage")
    table.add_column("done")
    for stage in _build_stages():
        table.add_row(stage.name, "yes" if stage.is_done(job) else "-")
    console.print(table)

    notes_path = job.stage_output("s4b_fuse")
    if notes_path.exists():
        notes = ir_io.load(NotesIR, notes_path)
        console.print(f"notes_fused: {len(notes.notes)} notes across {len(notes.runs)} runs")

    parts_path = job.stage_output("s5_disentangle")
    if parts_path.exists():
        parts = ir_io.load(PartsIR, parts_path)
        console.print(f"parts: {parts.part_stats}")

    tab_path = job.stage_output("s7_arrange")
    if tab_path.exists():
        tab = ir_io.load(TabIR, tab_path)
        for track in tab.tracks:
            console.print(f"track {track.name!r}: {sum(len(m.beats) for m in track.measures)} beats")


@app.command()
def batch(
    audio_dir: Path = typer.Argument(..., exists=True, file_okay=False, help="音源ファイルが入ったディレクトリ"),
    out_dir: Path = typer.Option(Path("out"), "--out-dir", help="ジョブ出力先の親ディレクトリ"),
    config: Path | None = typer.Option(None, "--config", help="設定ファイル (yaml)"),
    quality: str = typer.Option("standard", help="fast|standard|high"),
    workers: int = typer.Option(1, "--workers", help="現状シーケンシャル実行のみ対応"),
    pattern: str = typer.Option("*.wav,*.mp3,*.flac,*.m4a", "--pattern", help="対象拡張子(カンマ区切り glob)"),
) -> None:
    """複数音源を無人でバッチ処理する（実装指示書 T5-2）。

    1曲の失敗が他曲を止めない。Demucs と MuScriptor を同時ロードしないため
    （GPU メモリ競合回避、設計書 §12.1）、`--workers` は現状 1（シーケンシャル）
    のみサポートする。
    """
    if workers > 1:
        console.print(
            "[yellow]warning[/yellow]: --workers>1 は未対応。Demucs/MuScriptor の"
            " GPU メモリ競合を避けるためシーケンシャル実行する。"
        )

    globs = [p.strip() for p in pattern.split(",") if p.strip()]
    audio_files = sorted({f for g in globs for f in audio_dir.glob(g)})
    if not audio_files:
        console.print(f"[red]対象ファイルが見つからない[/red]: {audio_dir} ({pattern})")
        raise typer.Exit(code=1)

    cfg = TabForgeConfig.load(path=config, overrides={"job": {"quality": quality}})
    stages = _build_stages(cfg)

    results: list[tuple[Path, bool, str | None]] = []
    for audio in audio_files:
        job_dir = _resolve_job_dir(audio, out_dir)
        job = Job(job_dir=job_dir, source_audio=audio)
        try:
            job.run_pipeline(stages, cfg)
        except Exception as exc:  # noqa: BLE001 - 1曲の失敗で全体を止めない(T5-2 DoD)
            results.append((audio, False, str(exc)))
            console.print(f"[red]failed[/red] {audio.name}: {exc}")
        else:
            results.append((audio, True, None))
            console.print(f"[green]done[/green] {audio.name} -> {job_dir}")

    succeeded = sum(1 for _audio, ok, _err in results if ok)
    console.print(f"\nbatch complete: {succeeded}/{len(results)} succeeded")

    failures = [r for r in results if not r[1]]
    if failures:
        table = Table(title="Failures")
        table.add_column("file")
        table.add_column("error")
        for audio, _ok, err in failures:
            table.add_row(audio.name, err or "")
        console.print(table)


@app.command()
def export(
    job_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    format: str = typer.Option("gp5", help="カンマ区切り: gp5,musicxml"),
) -> None:
    """tab.json から再エクスポートのみ行う。"""
    from tabforge.stages import s9_export

    cfg = TabForgeConfig.load()
    job = Job(job_dir=job_dir)
    formats = [f.strip() for f in format.split(",") if f.strip()]
    s9_export.Stage(formats=formats).run(job, cfg)
    console.print(f"[green]exported[/green] {formats} -> {job_dir}")


if __name__ == "__main__":
    app()
