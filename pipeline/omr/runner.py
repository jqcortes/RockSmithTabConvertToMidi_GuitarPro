"""AudiverisRunner — Audiveris CLI subprocess 実行・タイムアウト管理"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import ClassVar

from pipeline.common import get_logger
from pipeline.omr.config import OmrConfigData
from pipeline.omr.errors import OmrExecutionError, OmrTimeoutError


class AudiverisRunner:
    """Audiveris CLI を subprocess で安全に実行するクラス。

    コマンドは必ずリスト形式で構築し `shell=False`（デフォルト）で実行することで
    コマンドインジェクションを防止する。
    タイムアウト時はプロセスを強制終了して `OmrTimeoutError` を raise する。
    """

    DEFAULT_OPTIONS: ClassVar[dict[str, str]] = {
        # Audiveris 5.3+ のタブラチュア検出スイッチ（6弦ギター / 4弦ベース）
        "org.audiveris.omr.sheet.ProcessingSwitches.sixStringTablatures": "true",
        "org.audiveris.omr.sheet.ProcessingSwitches.fourStringTablatures": "true",
        # ギター奏法記号
        "org.audiveris.omr.sheet.ProcessingSwitches.fingerings": "true",
        "org.audiveris.omr.sheet.ProcessingSwitches.pluckings": "true",
        "org.audiveris.omr.sheet.ProcessingSwitches.tremolos": "true",
        "org.audiveris.omr.sheet.ProcessingSwitches.articulations": "true",
        # 品質チューニング
        "org.audiveris.omr.sig.inter.AbstractInter.minGrade": "0.35",
    }

    def run(
        self,
        image_path: Path,
        output_dir: Path,
        config: OmrConfigData,
    ) -> dict[str, float | int | str | bool]:
        """Audiveris CLI を実行して metrics dict を返す。

        Args:
            image_path: 処理対象の前処理済み PNG。
            output_dir: Audiveris が MusicXML を書き込む出力ディレクトリ。
            config: JAR パス・タイムアウト・追加オプションを含む設定。

        Returns:
            ``elapsed_seconds`` を含む metrics dict。

        Raises:
            OmrTimeoutError: タイムアウトが発生した場合。
            OmrExecutionError: Audiveris が 0 以外の終了コードを返した場合。
        """
        logger = get_logger(__name__)
        cmd = self._build_command(image_path, output_dir, config)

        logger.debug("audiveris_start", cmd=cmd)
        start = time.monotonic()

        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as proc:
            try:
                stdout, stderr = proc.communicate(timeout=config.timeout_seconds)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                raise OmrTimeoutError(
                    f"Audiveris が {config.timeout_seconds} 秒以内に完了しませんでした。"
                )

        elapsed = time.monotonic() - start
        logger.debug(
            "audiveris_finished",
            elapsed_seconds=elapsed,
            returncode=proc.returncode,
            stdout=stdout,
            stderr=stderr,
        )

        if proc.returncode != 0:
            raise OmrExecutionError(
                f"Audiveris が終了コード {proc.returncode} で失敗しました。"
                f" stderr: {stderr}"
            )

        return {"elapsed_seconds": float(elapsed)}

    def _build_command(
        self,
        image_path: Path,
        output_dir: Path,
        config: OmrConfigData,
    ) -> list[str]:
        """実行コマンドをリスト形式で構築する。"""
        cmd: list[str]

        # MSI 配布版は app/audiveris.jar + 依存JAR群の classpath 起動が必要。
        if (
            config.jar_path.name.lower() == "audiveris.jar"
            and config.jar_path.parent.name.lower() == "app"
        ):
            classpath = str(config.jar_path.parent / "*")
            cmd = [
                "java",
                "-cp",
                classpath,
                # Audiveris.cfg に記載された必須 JVM オプション（Java 17+ との互換）
                "--enable-native-access=ALL-UNNAMED",
                "--add-exports=java.desktop/sun.awt.image=ALL-UNNAMED",
                "-Dfile.encoding=UTF-8",
                "-Xms512m",
                "Audiveris",
                "-batch",
                "-transcribe",
                "-export",
            ]
        else:
            cmd = [
                "java",
                "-jar",
                str(config.jar_path),
                "-batch",
                "-transcribe",
                "-export",
            ]

        # デフォルトオプション + 設定ファイル追加オプションを付加
        # Audiveris CLI の正式フラグは -constant (ヘルプ確認済み)。
        # -option は古い表記で 5.10 では無効のため -constant を使用する。
        all_options = {**self.DEFAULT_OPTIONS, **config.extra_options}
        for key, value in all_options.items():
            cmd += ["-constant", f"{key}={value}"]

        cmd += ["-output", str(output_dir)]
        cmd += ["--", str(image_path)]

        return cmd
