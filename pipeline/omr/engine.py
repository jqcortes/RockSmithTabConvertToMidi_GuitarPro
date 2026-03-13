"""OmrEngine — Java 実行環境検証"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from pipeline.common import get_logger
from pipeline.omr.errors import OmrEnvironmentError

_JAVA_VERSION_RE = re.compile(r'"(\d+)(?:\.(\d+))?')


def _parse_java_major(stderr: str) -> int:
    """java -version の stderr 出力からメジャーバージョンを返す。

    OpenJDK 9 以降は '"17.x.x"' 形式。
    旧形式 (Java 8) は '"1.8.x"' → major=1, minor=8 → 8 と解釈する。

    Raises:
        OmrEnvironmentError: バージョン文字列が解析できない場合。
    """
    match = _JAVA_VERSION_RE.search(stderr)
    if not match:
        raise OmrEnvironmentError(
            f"Java バージョン文字列を解析できませんでした: {stderr!r}"
        )
    major = int(match.group(1))
    # "1.8.x" 形式 (Java 8 以前) は group(2) が minor バージョン
    if major == 1 and match.group(2) is not None:
        major = int(match.group(2))
    return major


class OmrEngine:
    """Audiveris 実行前の環境検証を担う静的ユーティリティクラス。"""

    @staticmethod
    def validate_environment(jar_path: Path) -> None:
        """Java 17+ と JAR ファイルの存在を検証する。

        Args:
            jar_path: Audiveris JAR ファイルのパス。

        Raises:
            OmrEnvironmentError: Java が見つからない・バージョン不足・JAR 不在の場合。
        """
        logger = get_logger(__name__)

        # ── Java バージョン確認 ──────────────────────────────────────────
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, OSError) as exc:
            raise OmrEnvironmentError(
                f"Java が見つかりません。PATH を確認してください: {exc}"
            ) from exc

        major = _parse_java_major(result.stderr)
        if major < 17:
            raise OmrEnvironmentError(
                f"Java 17 以上が必要ですが、バージョン {major} が検出されました。"
            )

        # ── JAR 存在確認 ─────────────────────────────────────────────────
        if not jar_path.exists():
            raise OmrEnvironmentError(
                f"Audiveris JAR が見つかりません: {jar_path}"
            )

        logger.info(
            "omr_environment_ok",
            java_major=major,
            jar_path=str(jar_path),
        )
