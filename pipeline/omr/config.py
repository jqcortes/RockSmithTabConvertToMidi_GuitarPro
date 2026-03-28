"""
pipeline/omr/config.py — Audiveris 実行設定のロード

環境変数 → config/audiveris.properties → デフォルト値の優先順で設定を解決する。

Public API:
    OmrConfigData — 不変の設定データオブジェクト
    OmrConfig     — 設定ロードユーティリティ
"""

from __future__ import annotations

import configparser
import os
import re
from dataclasses import dataclass
from pathlib import Path

from pipeline.common import get_logger

_log = get_logger(__name__)

_DEFAULT_TIMEOUT: int = 300
_OPTION_PREFIX: str = "audiveris.option."


def _normalize_path_value(value: str) -> str:
    normalized = value.strip()
    if (normalized.startswith('"') and normalized.endswith('"')) or (
        normalized.startswith("'") and normalized.endswith("'")
    ):
        return normalized[1:-1].strip()
    return normalized


@dataclass(frozen=True)
class OmrConfigData:
    """Audiveris 実行設定（不変）。

    Attributes:
        jar_path:        Audiveris JAR ファイルのパス
        timeout_seconds: subprocess タイムアウト秒数（デフォルト: 300）
        extra_options:   audiveris.properties から読み込んだ追加 CLI オプション
    """

    jar_path: Path
    timeout_seconds: int
    extra_options: dict[str, str]
    subprocess_env: dict[str, str] | None = None
    ocr_language: str = "eng"


class OmrConfig:
    """Audiveris 設定ローダー。

    優先度:
    1. 環境変数 AUDIVERIS_JAR / AUDIVERIS_TIMEOUT
    2. config/audiveris.properties の audiveris.jar / audiveris.timeout
    3. デフォルト値（timeout=300）
    """

    @staticmethod
    def load(
        properties_path: Path = Path("config/audiveris.properties"),
    ) -> OmrConfigData:
        """設定を優先度順に解決して OmrConfigData を返す。

        Args:
            properties_path: audiveris.properties のパス（存在しない場合はデフォルト値を使用）

        Returns:
            OmrConfigData — 不変の設定データ

        Raises:
            OmrEnvironmentError: JAR パスが環境変数にも properties にも設定されていない場合
        """
        # properties ファイルを読み込む（存在しない場合は空の parser）
        parser = configparser.ConfigParser()
        parser.optionxform = str  # type: ignore[assignment]  # キー名の大文字・小文字を保持する
        props_loaded = False
        if properties_path.exists():
            parser.read(str(properties_path), encoding="utf-8")
            props_loaded = True
            _log.info("omr_config_loaded", path=str(properties_path))
        else:
            _log.warning("omr_config_missing", path=str(properties_path))

        # --- JAR パス解決: env var > properties > エラー ---
        jar_str = os.environ.get("AUDIVERIS_JAR")
        if jar_str is None and props_loaded:
            jar_str = parser.defaults().get("audiveris.jar")
        if jar_str is None:
            from pipeline.omr.errors import OmrEnvironmentError
            raise OmrEnvironmentError(
                "Audiveris JAR パスが未設定です。"
                " AUDIVERIS_JAR 環境変数または config/audiveris.properties の"
                " audiveris.jar キーに設定してください。"
            )
        jar_path = Path(_normalize_path_value(jar_str))

        # --- タイムアウト解決: env var > properties > 300 ---
        timeout_str = os.environ.get("AUDIVERIS_TIMEOUT")
        if timeout_str is None and props_loaded:
            timeout_str = parser.defaults().get("audiveris.timeout")
        timeout_seconds = int(timeout_str) if timeout_str is not None else _DEFAULT_TIMEOUT

        # --- 追加オプション解決: audiveris.option.* キー ---
        extra_options: dict[str, str] = {}
        if props_loaded:
            for key, value in parser.defaults().items():
                if key.startswith(_OPTION_PREFIX):
                    option_key = key[len(_OPTION_PREFIX):]
                    extra_options[option_key] = value

        ocr_language = str(
            extra_options.get(
                "org.audiveris.omr.text.tesseract.TesseractOCR.language",
                "eng",
            )
        ).strip() or "eng"
        subprocess_env = _resolve_ocr_subprocess_env(jar_path, ocr_language)

        _log.info(
            "omr_config_resolved",
            jar_path=str(jar_path),
            timeout_seconds=timeout_seconds,
            extra_option_count=len(extra_options),
            ocr_language=ocr_language,
            tessdata_prefix=(subprocess_env or {}).get("TESSDATA_PREFIX"),
        )

        return OmrConfigData(
            jar_path=jar_path,
            timeout_seconds=timeout_seconds,
            extra_options=extra_options,
            subprocess_env=subprocess_env,
            ocr_language=ocr_language,
        )


def _resolve_ocr_subprocess_env(jar_path: Path, ocr_language: str) -> dict[str, str] | None:
    """利用可能な tessdata を探索して subprocess 用 env を返す。"""
    candidate_dirs: list[Path] = []

    # 例: C:/Program Files/Audiveris/app/audiveris.jar
    # -> C:/Program Files/Audiveris/tessdata
    # -> C:/Program Files/Audiveris/runtime/tessdata
    app_dir = jar_path.parent
    install_root = app_dir.parent if app_dir.name.lower() == "app" else app_dir

    candidate_dirs.extend(
        [
            install_root / "tessdata",
            install_root / "runtime" / "tessdata",
            Path("C:/Program Files/Audiveris/tessdata"),
            Path("C:/Program Files/Audiveris/runtime/tessdata"),
        ]
    )

    # 重複除去しつつ順序保持
    unique_dirs: list[Path] = []
    seen: set[str] = set()
    for d in candidate_dirs:
        key = str(d).lower()
        if key not in seen:
            seen.add(key)
            unique_dirs.append(d)

    languages = [t for t in re.split(r"[+,]", ocr_language) if t]
    if not languages:
        languages = ["eng"]

    for tessdata_dir in unique_dirs:
        if not tessdata_dir.exists() or not tessdata_dir.is_dir():
            continue

        if all((tessdata_dir / f"{lang}.traineddata").exists() for lang in languages):
            return {"TESSDATA_PREFIX": str(tessdata_dir)}

    return None
