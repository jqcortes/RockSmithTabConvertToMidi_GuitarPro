"""OmrEngine ユニットテスト — Task 3: Java 環境検証"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.omr.errors import OmrEnvironmentError


class TestValidateEnvironmentSuccess:
    """Java 17+ かつ JAR 存在時は例外なし"""

    def test_java17_detected_no_exception(self, tmp_path: Path) -> None:
        """java -version が 17 を返し、JAR が存在する場合は例外を raise しない"""
        from pipeline.omr.engine import OmrEngine

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = 'openjdk version "17.0.8" 2023-07-18'

        with patch("subprocess.run", return_value=mock_result):
            OmrEngine.validate_environment(fake_jar)  # raises しないこと

    def test_java21_also_accepted(self, tmp_path: Path) -> None:
        """Java 21 (17 超) も受け入れられること"""
        from pipeline.omr.engine import OmrEngine

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = 'openjdk version "21.0.1" 2023-10-17'

        with patch("subprocess.run", return_value=mock_result):
            OmrEngine.validate_environment(fake_jar)  # raises しないこと


class TestValidateEnvironmentJavaMissing:
    """Java が見つからない場合は OmrEnvironmentError"""

    def test_java_not_found_raises(self, tmp_path: Path) -> None:
        """`java` コマンドが FileNotFoundError を raise する場合"""
        from pipeline.omr.engine import OmrEngine

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()

        with patch("subprocess.run", side_effect=FileNotFoundError("java not found")):
            with pytest.raises(OmrEnvironmentError, match="Java"):
                OmrEngine.validate_environment(fake_jar)

    def test_java_subprocess_error_raises(self, tmp_path: Path) -> None:
        """subprocess が OSError を raise する場合も OmrEnvironmentError に変換される"""
        from pipeline.omr.engine import OmrEngine

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()

        with patch("subprocess.run", side_effect=OSError("execution failed")):
            with pytest.raises(OmrEnvironmentError, match="Java"):
                OmrEngine.validate_environment(fake_jar)


class TestValidateEnvironmentJavaTooOld:
    """Java バージョンが 17 未満の場合は OmrEnvironmentError"""

    def test_java11_raises(self, tmp_path: Path) -> None:
        """Java 11 は拒否される"""
        from pipeline.omr.engine import OmrEngine

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = 'openjdk version "11.0.20" 2023-07-18'

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(OmrEnvironmentError, match="Java 17"):
                OmrEngine.validate_environment(fake_jar)

    def test_java8_raises(self, tmp_path: Path) -> None:
        """Java 8 (1.8.x) は拒否される"""
        from pipeline.omr.engine import OmrEngine

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = 'java version "1.8.0_381"'

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(OmrEnvironmentError, match="Java 17"):
                OmrEngine.validate_environment(fake_jar)

    def test_version_not_parseable_raises(self, tmp_path: Path) -> None:
        """バージョン文字列が解析できない場合も OmrEnvironmentError"""
        from pipeline.omr.engine import OmrEngine

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = "some unexpected output without version"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(OmrEnvironmentError, match="Java"):
                OmrEngine.validate_environment(fake_jar)


class TestValidateEnvironmentJarMissing:
    """JAR ファイルが存在しない場合は OmrEnvironmentError"""

    def test_missing_jar_raises(self, tmp_path: Path) -> None:
        """JAR ファイルが存在しない場合 OmrEnvironmentError を raise し、パスを含む"""
        from pipeline.omr.engine import OmrEngine

        missing_jar = tmp_path / "nonexistent" / "audiveris.jar"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = 'openjdk version "17.0.8" 2023-07-18'

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(OmrEnvironmentError, match=re.escape(str(missing_jar))):
                OmrEngine.validate_environment(missing_jar)

    def test_error_message_contains_jar_path(self, tmp_path: Path) -> None:
        """エラーメッセージに JAR パスが含まれること"""
        from pipeline.omr.engine import OmrEngine

        missing_jar = tmp_path / "audiveris-5.3.jar"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = 'openjdk version "17.0.8" 2023-07-18'

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(OmrEnvironmentError) as exc_info:
                OmrEngine.validate_environment(missing_jar)
            assert "audiveris-5.3.jar" in str(exc_info.value)


class TestValidateEnvironmentLogging:
    """検証結果が structlog で記録されること"""

    def test_success_is_logged(self, tmp_path: Path) -> None:
        """成功時に structlog.get_logger().info() が呼ばれること"""
        from pipeline.omr.engine import OmrEngine

        fake_jar = tmp_path / "audiveris.jar"
        fake_jar.touch()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = 'openjdk version "17.0.8" 2023-07-18'

        with patch("subprocess.run", return_value=mock_result):
            with patch("pipeline.omr.engine.get_logger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger
                OmrEngine.validate_environment(fake_jar)
                mock_logger.info.assert_called_once()
