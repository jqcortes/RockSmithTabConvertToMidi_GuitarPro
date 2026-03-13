"""transcribe() — OMR ドメインの公開エントリポイント"""

from __future__ import annotations

from pathlib import Path

from pipeline.common import StepResult, get_logger
from pipeline.omr.config import OmrConfig
from pipeline.omr.engine import OmrEngine
from pipeline.omr.errors import OmrOutputError
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
    run_metrics = actual_runner.run(image_path, output_dir, config)
    elapsed: float = float(run_metrics.get("elapsed_seconds", 0.0))

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
        },
    )
