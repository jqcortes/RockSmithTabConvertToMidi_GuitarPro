"""
tests/unit/test_omr/test_config.py — OmrConfig のユニットテスト

Task 7.2 対応。
env var → config file → default の優先度解決をテストする。
"""

from __future__ import annotations

import configparser
from pathlib import Path
from unittest.mock import patch

import pytest


class TestOmrConfigDefaults:
    """設定ファイル・環境変数がない場合はデフォルト値を使うこと"""

    def test_default_timeout_is_300(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()
        with patch.dict("os.environ", {"AUDIVERIS_JAR": str(fake_jar)}):
            result = OmrConfig.load(properties_path=tmp_path / "nonexistent.properties")
        assert result.timeout_seconds == 300

    def test_default_extra_options_empty(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        with patch.dict("os.environ", {}, clear=False):
            # AUDIVERIS_JAR を明示的に設定して OmrConfigError を避ける
            fake_jar = tmp_path / "audiveris.jar"
            fake_jar.touch()
            with patch.dict("os.environ", {"AUDIVERIS_JAR": str(fake_jar)}):
                result = OmrConfig.load(properties_path=tmp_path / "nonexistent.properties")
        assert result.extra_options == {}

    def test_missing_properties_file_warns_but_continues(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        from pipeline.omr.config import OmrConfig

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()
        with patch.dict("os.environ", {"AUDIVERIS_JAR": str(fake_jar)}):
            result = OmrConfig.load(properties_path=tmp_path / "nonexistent.properties")
        # エラーにならず結果が返ること
        assert result.timeout_seconds == 300


class TestOmrConfigJarPath:
    """JAR パスの優先度: 環境変数 > properties ファイル"""

    def test_env_var_jar_takes_priority(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        env_jar = tmp_path / "env_audiveris.jar"
        env_jar.touch()
        props_jar = tmp_path / "props_audiveris.jar"
        props_jar.touch()

        props_file = tmp_path / "audiveris.properties"
        props_file.write_text(f"[DEFAULT]\naudiveris.jar = {props_jar}\n")

        with patch.dict("os.environ", {"AUDIVERIS_JAR": str(env_jar)}):
            result = OmrConfig.load(properties_path=props_file)

        assert result.jar_path == env_jar

    def test_properties_jar_used_when_no_env_var(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        props_jar = tmp_path / "props_audiveris.jar"
        props_jar.touch()
        props_file = tmp_path / "audiveris.properties"
        props_file.write_text(f"[DEFAULT]\naudiveris.jar = {props_jar}\n")

        env = {k: v for k, v in __import__("os").environ.items() if k != "AUDIVERIS_JAR"}
        with patch.dict("os.environ", env, clear=True):
            result = OmrConfig.load(properties_path=props_file)

        assert result.jar_path == props_jar

    def test_jar_path_is_path_object(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()
        with patch.dict("os.environ", {"AUDIVERIS_JAR": str(fake_jar)}):
            result = OmrConfig.load(properties_path=tmp_path / "none.properties")

        assert isinstance(result.jar_path, Path)

    def test_properties_jar_with_quotes_is_normalized(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        props_jar = tmp_path / "props_audiveris.jar"
        props_jar.touch()
        props_file = tmp_path / "audiveris.properties"
        props_file.write_text(f"[DEFAULT]\naudiveris.jar = \"{props_jar}\"\n")

        env = {k: v for k, v in __import__("os").environ.items() if k != "AUDIVERIS_JAR"}
        with patch.dict("os.environ", env, clear=True):
            result = OmrConfig.load(properties_path=props_file)

        assert result.jar_path == props_jar

    def test_env_var_jar_with_quotes_is_normalized(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        env_jar = tmp_path / "env_audiveris.jar"
        env_jar.touch()

        with patch.dict("os.environ", {"AUDIVERIS_JAR": f'"{env_jar}"'}):
            result = OmrConfig.load(properties_path=tmp_path / "none.properties")

        assert result.jar_path == env_jar


class TestOmrConfigTimeout:
    """タイムアウトの優先度: 環境変数 > properties ファイル > 300 秒デフォルト"""

    def test_env_var_timeout_takes_priority(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()
        props_file = tmp_path / "audiveris.properties"
        props_file.write_text(f"[DEFAULT]\naudiveris.jar = {fake_jar}\naudiveris.timeout = 120\n")

        with patch.dict("os.environ", {"AUDIVERIS_JAR": str(fake_jar), "AUDIVERIS_TIMEOUT": "600"}):
            result = OmrConfig.load(properties_path=props_file)

        assert result.timeout_seconds == 600

    def test_properties_timeout_used_when_no_env(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()
        props_file = tmp_path / "audiveris.properties"
        props_file.write_text(f"[DEFAULT]\naudiveris.jar = {fake_jar}\naudiveris.timeout = 120\n")

        env = {k: v for k, v in __import__("os").environ.items()
               if k not in ("AUDIVERIS_JAR", "AUDIVERIS_TIMEOUT")}
        with patch.dict("os.environ", env, clear=True):
            result = OmrConfig.load(properties_path=props_file)

        assert result.timeout_seconds == 120

    def test_default_timeout_300_when_nothing_set(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()
        env = {k: v for k, v in __import__("os").environ.items()
               if k not in ("AUDIVERIS_JAR", "AUDIVERIS_TIMEOUT")}
        with patch.dict("os.environ", {**env, "AUDIVERIS_JAR": str(fake_jar)}, clear=True):
            result = OmrConfig.load(properties_path=tmp_path / "none.properties")

        assert result.timeout_seconds == 300


class TestOmrConfigExtraOptions:
    """properties ファイルの audiveris.option.* キーが extra_options に入ること"""

    def test_extra_options_loaded_from_properties(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()
        props_file = tmp_path / "audiveris.properties"
        props_file.write_text(
            f"[DEFAULT]\n"
            f"audiveris.jar = {fake_jar}\n"
            f"audiveris.option.org.audiveris.omr.sig.inter.AbstractInter.minGrade = 0.3\n"
        )

        env = {k: v for k, v in __import__("os").environ.items()
               if k not in ("AUDIVERIS_JAR", "AUDIVERIS_TIMEOUT")}
        with patch.dict("os.environ", env, clear=True):
            result = OmrConfig.load(properties_path=props_file)

        assert "org.audiveris.omr.sig.inter.AbstractInter.minGrade" in result.extra_options
        assert result.extra_options["org.audiveris.omr.sig.inter.AbstractInter.minGrade"] == "0.3"

    def test_extra_options_empty_when_no_option_keys(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()
        env = {k: v for k, v in __import__("os").environ.items()
               if k not in ("AUDIVERIS_JAR", "AUDIVERIS_TIMEOUT")}
        with patch.dict("os.environ", {**env, "AUDIVERIS_JAR": str(fake_jar)}, clear=True):
            result = OmrConfig.load(properties_path=tmp_path / "none.properties")

        assert result.extra_options == {}


class TestOmrConfigOcrEnvironment:
    """OCR 言語設定と TESSDATA_PREFIX 解決のテスト。"""

    def test_resolves_tessdata_prefix_when_traineddata_exists(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        app_dir = tmp_path / "app"
        app_dir.mkdir()
        jar = app_dir / "audiveris.jar"
        jar.touch()

        tessdata = tmp_path / "tessdata"
        tessdata.mkdir()
        (tessdata / "eng.traineddata").touch()

        props = tmp_path / "audiveris.properties"
        props.write_text(
            "\n".join(
                [
                    "[DEFAULT]",
                    f"audiveris.jar = {jar}",
                    "audiveris.option.org.audiveris.omr.text.tesseract.TesseractOCR.language = eng",
                ]
            ),
            encoding="utf-8",
        )

        env = {k: v for k, v in __import__("os").environ.items() if k not in ("AUDIVERIS_JAR", "AUDIVERIS_TIMEOUT")}
        with patch.dict("os.environ", env, clear=True):
            result = OmrConfig.load(properties_path=props)

        assert result.ocr_language == "eng"
        assert result.subprocess_env is not None
        assert result.subprocess_env.get("TESSDATA_PREFIX") == str(tessdata)

    def test_subprocess_env_none_when_traineddata_missing(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        jar = tmp_path / "audiveris.jar"
        jar.touch()
        props = tmp_path / "audiveris.properties"
        props.write_text(f"[DEFAULT]\naudiveris.jar = {jar}\n", encoding="utf-8")

        env = {k: v for k, v in __import__("os").environ.items() if k not in ("AUDIVERIS_JAR", "AUDIVERIS_TIMEOUT")}
        with patch.dict("os.environ", env, clear=True):
            result = OmrConfig.load(properties_path=props)

        assert result.subprocess_env is None


class TestOmrConfigDataImmutability:
    """OmrConfigData は frozen dataclass（不変）であること"""

    def test_config_data_is_frozen(self, tmp_path: Path) -> None:
        from pipeline.omr.config import OmrConfig

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()
        with patch.dict("os.environ", {"AUDIVERIS_JAR": str(fake_jar)}):
            result = OmrConfig.load(properties_path=tmp_path / "none.properties")

        with pytest.raises((AttributeError, TypeError)):
            result.timeout_seconds = 999  # type: ignore[misc]
