"""transcribe() — OMR ドメインの公開エントリポイント"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from pipeline.common import StepResult, get_logger
from pipeline.omr.config import OmrConfig, OmrConfigData
from pipeline.omr.engine import OmrEngine
from pipeline.omr.errors import OmrExecutionError, OmrOutputError
from pipeline.omr.finder import MusicXmlFinder
from pipeline.omr.runner import AudiverisRunner


def transcribe(
    image_path: Path,
    output_dir: Path,
    *,
    runner: AudiverisRunner | None = None,
    properties_path: Path = Path("config/audiveris.properties"),
) -> StepResult:
    """前処理済み PNG 画像を Audiveris に通して MusicXML パスを返す。

    処理順序:
    1. OmrConfig.load() で設定解決
    2. OmrEngine.validate_environment() で Java / JAR 確認
    3. キャッシュ確認（MusicXmlFinder.find() を先行試行）
    4. キャッシュミス時: AudiverisRunner.run() を実行
    5. MusicXmlFinder.find() で出力 MusicXML を探索・検証
    6. StepResult を返す

    Args:
        image_path: 前処理済み PNG ファイルパス。
        output_dir: Audiveris が MusicXML を出力するディレクトリ。
        runner: テスト用の AudiverisRunner インスタンス。None の場合はデフォルト生成。

    Returns:
        success=True の StepResult。metrics に cached・elapsed_seconds・musicxml_path を含む。

    Raises:
        OmrEnvironmentError: 環境検証失敗。
        OmrTimeoutError: Audiveris タイムアウト。
        OmrExecutionError: Audiveris 非0終了。
        OmrOutputError: MusicXML が見つからない・破損。
    """
    logger = get_logger(__name__)

    # 1. 設定ロード
    config = OmrConfig.load(properties_path=properties_path)

    # 2. 環境検証
    OmrEngine.validate_environment(config.jar_path)

    # 3. キャッシュ確認
    try:
        musicxml_path = MusicXmlFinder.find(output_dir, image_path.stem)
        logger.info("omr_cache_hit", musicxml_path=str(musicxml_path))
        return StepResult.ok(
            output_path=musicxml_path,
            metrics={
                "cached": True,
                "elapsed_seconds": 0.0,
                "musicxml_path": str(musicxml_path),
            },
        )
    except OmrOutputError:
        logger.info("omr_cache_miss", image_path=str(image_path))

    # 4. Audiveris CLI 実行
    actual_runner = runner if runner is not None else AudiverisRunner()
    fallback_used = False
    try:
        run_metrics = actual_runner.run(image_path, output_dir, config)
        elapsed: float = float(run_metrics.get("elapsed_seconds", 0.0))
    except OmrExecutionError as primary_error:
        logger.warning(
            "omr_primary_failed",
            image_path=str(image_path),
            reason=str(primary_error),
        )
        elapsed = _retry_with_curves_skip(image_path, output_dir, config, actual_runner)
        fallback_used = True
        logger.info("omr_fallback_succeeded", image_path=str(image_path), elapsed_seconds=elapsed)

    # 5. MusicXML 探索・検証
    musicxml_path = MusicXmlFinder.find(output_dir, image_path.stem)

    logger.info(
        "omr_complete",
        musicxml_path=str(musicxml_path),
        elapsed_seconds=elapsed,
    )

    return StepResult.ok(
        output_path=musicxml_path,
        metrics={
            "cached": False,
            "elapsed_seconds": elapsed,
            "musicxml_path": str(musicxml_path),
            "fallback_curves_skip": fallback_used,
        },
    )


def _retry_with_curves_skip(
    image_path: Path,
    output_dir: Path,
    config: OmrConfigData,
    runner: AudiverisRunner,
) -> float:
    """失敗時に CHORDS まで実行して CURVES をスキップして再開する。"""
    logger = get_logger(__name__)

    first_metrics = runner.run(
        image_path,
        output_dir,
        config,
        workflow="chords-save",
    )

    omr_path = _find_first_file(output_dir, "*.omr")
    if omr_path is None:
        raise OmrOutputError(f"Fallback 用 .omr が見つかりません: {output_dir}")

    patched = _append_steps_in_omr(omr_path, ["CURVES"])
    logger.info(
        "omr_fallback_patch",
        omr_path=str(omr_path),
        patched=patched,
    )

    second_metrics = runner.run(
        omr_path,
        output_dir,
        config,
        workflow="transcribe-export",
    )

    return float(first_metrics.get("elapsed_seconds", 0.0)) + float(
        second_metrics.get("elapsed_seconds", 0.0)
    )


def _find_first_file(directory: Path, pattern: str) -> Path | None:
    files = sorted(directory.glob(pattern))
    if not files:
        return None
    return files[0]


def _append_steps_in_omr(omr_path: Path, extra_steps: list[str]) -> bool:
    """.omr 内 book.xml の <steps> に指定ステップを追記する。"""
    tmp_path = omr_path.with_suffix(".omr.tmp")
    changed = False

    with zipfile.ZipFile(omr_path, "r") as zin:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "book.xml":
                    xml = data.decode("utf-8")
                    match = re.search(r"<steps>(.*?)</steps>", xml, re.DOTALL)
                    current_steps = match.group(1).strip().split() if match else []
                    to_add = [s for s in extra_steps if s not in current_steps]
                    if to_add:
                        new_steps = " ".join(current_steps + to_add)
                        xml = re.sub(
                            r"(<steps>)(.*?)(</steps>)",
                            lambda m: f"{m.group(1)}{new_steps}{m.group(3)}",
                            xml,
                            flags=re.DOTALL,
                        )
                        data = xml.encode("utf-8")
                        changed = True
                zout.writestr(item, data)

    tmp_path.replace(omr_path)
    return changed
