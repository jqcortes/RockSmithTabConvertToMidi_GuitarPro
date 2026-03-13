"""AudiverisRunner ユニットテスト — Task 4: CLI 実行・タイムアウト管理"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from pipeline.omr.config import OmrConfigData
from pipeline.omr.errors import OmrExecutionError, OmrTimeoutError


def _make_config(tmp_path: Path, timeout: int = 300) -> OmrConfigData:
    """テスト用 OmrConfigData を生成するヘルパー"""
    jar = tmp_path / "audiveris.jar"
    jar.touch()
    return OmrConfigData(
        jar_path=jar,
        timeout_seconds=timeout,
        extra_options={},
    )


class TestAudiverisRunnerCommandBuilding:
    """コマンドがリスト形式・正しい構造で構築されること"""

    def test_command_starts_with_java_jar(self, tmp_path: Path) -> None:
        """コマンドの先頭が ["java", "-jar", <jar_path>] であること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()

        captured: list[list[str]] = []

        def fake_popen(cmd: list[str], **kwargs: object) -> MagicMock:
            captured.append(list(cmd))
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_proc.__enter__ = lambda s: s
            mock_proc.__exit__ = MagicMock(return_value=False)
            return mock_proc

        with patch("subprocess.Popen", side_effect=fake_popen):
            runner.run(image, output_dir, config)

        cmd = captured[0]
        assert cmd[0] == "java"
        assert cmd[1] == "-jar"
        assert cmd[2] == str(config.jar_path)

    def test_command_includes_batch_transcribe_export(self, tmp_path: Path) -> None:
        """-batch, -transcribe, -export フラグが含まれること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()
        captured: list[list[str]] = []

        def fake_popen(cmd: list[str], **kwargs: object) -> MagicMock:
            captured.append(list(cmd))
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_proc.__enter__ = lambda s: s
            mock_proc.__exit__ = MagicMock(return_value=False)
            return mock_proc

        with patch("subprocess.Popen", side_effect=fake_popen):
            runner.run(image, output_dir, config)

        cmd = captured[0]
        assert "-batch" in cmd
        assert "-transcribe" in cmd
        assert "-export" in cmd

    def test_command_includes_output_dir(self, tmp_path: Path) -> None:
        """-output <dir> がコマンドに含まれること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()
        captured: list[list[str]] = []

        def fake_popen(cmd: list[str], **kwargs: object) -> MagicMock:
            captured.append(list(cmd))
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_proc.__enter__ = lambda s: s
            mock_proc.__exit__ = MagicMock(return_value=False)
            return mock_proc

        with patch("subprocess.Popen", side_effect=fake_popen):
            runner.run(image, output_dir, config)

        cmd = captured[0]
        out_idx = cmd.index("-output")
        assert cmd[out_idx + 1] == str(output_dir)

    def test_command_ends_with_separator_and_image(self, tmp_path: Path) -> None:
        """コマンド末尾が ['--', <image_path>] であること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()
        captured: list[list[str]] = []

        def fake_popen(cmd: list[str], **kwargs: object) -> MagicMock:
            captured.append(list(cmd))
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_proc.__enter__ = lambda s: s
            mock_proc.__exit__ = MagicMock(return_value=False)
            return mock_proc

        with patch("subprocess.Popen", side_effect=fake_popen):
            runner.run(image, output_dir, config)

        cmd = captured[0]
        assert cmd[-2] == "--"
        assert cmd[-1] == str(image)

    def test_command_is_list_not_string(self, tmp_path: Path) -> None:
        """コマンドがリスト形式であること（shell=False によるインジェクション防止）"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()
        captured_kwargs: list[dict[str, object]] = []

        def fake_popen(cmd: object, **kwargs: object) -> MagicMock:
            assert isinstance(cmd, list), "コマンドはリスト形式であること"
            captured_kwargs.append(dict(kwargs))
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_proc.__enter__ = lambda s: s
            mock_proc.__exit__ = MagicMock(return_value=False)
            return mock_proc

        with patch("subprocess.Popen", side_effect=fake_popen):
            runner.run(image, output_dir, config)

        # shell=False がデフォルト（または明示的に False）
        assert captured_kwargs[0].get("shell", False) is False

    def test_default_options_included(self, tmp_path: Path) -> None:
        """DEFAULT_OPTIONS の -option key=value がコマンドに含まれること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()
        captured: list[list[str]] = []

        def fake_popen(cmd: list[str], **kwargs: object) -> MagicMock:
            captured.append(list(cmd))
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_proc.__enter__ = lambda s: s
            mock_proc.__exit__ = MagicMock(return_value=False)
            return mock_proc

        with patch("subprocess.Popen", side_effect=fake_popen):
            runner.run(image, output_dir, config)

        cmd = captured[0]
        cmd_str = " ".join(cmd)
        assert "useTablature=true" in cmd_str
        assert "minGrade=0.35" in cmd_str

    def test_extra_options_from_config_included(self, tmp_path: Path) -> None:
        """config.extra_options の内容もコマンドに含まれること"""
        from pipeline.omr.runner import AudiverisRunner

        jar = tmp_path / "audiveris.jar"
        jar.touch()
        config = OmrConfigData(
            jar_path=jar,
            timeout_seconds=300,
            extra_options={"org.audiveris.custom.key": "customValue"},
        )
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()
        captured: list[list[str]] = []

        def fake_popen(cmd: list[str], **kwargs: object) -> MagicMock:
            captured.append(list(cmd))
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_proc.__enter__ = lambda s: s
            mock_proc.__exit__ = MagicMock(return_value=False)
            return mock_proc

        with patch("subprocess.Popen", side_effect=fake_popen):
            runner.run(image, output_dir, config)

        cmd = captured[0]
        cmd_str = " ".join(cmd)
        assert "org.audiveris.custom.key=customValue" in cmd_str

    def test_msi_layout_uses_classpath_mode(self, tmp_path: Path) -> None:
        """MSI配布の app/audiveris.jar 指定時は -cp app/* + Audiveris で起動すること"""
        from pipeline.omr.runner import AudiverisRunner

        app_dir = tmp_path / "app"
        app_dir.mkdir(parents=True)
        jar = app_dir / "audiveris.jar"
        jar.touch()
        config = OmrConfigData(jar_path=jar, timeout_seconds=300, extra_options={})

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()
        captured: list[list[str]] = []

        def fake_popen(cmd: list[str], **kwargs: object) -> MagicMock:
            captured.append(list(cmd))
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_proc.__enter__ = lambda s: s
            mock_proc.__exit__ = MagicMock(return_value=False)
            return mock_proc

        with patch("subprocess.Popen", side_effect=fake_popen):
            runner.run(image, output_dir, config)

        cmd = captured[0]
        assert cmd[0] == "java"
        assert cmd[1] == "-cp"
        assert cmd[2].endswith("app\\*") or cmd[2].endswith("app/*")
        assert cmd[3] == "Audiveris"


class TestAudiverisRunnerSuccess:
    """正常終了時の戻り値検証"""

    def test_returns_metrics_dict(self, tmp_path: Path) -> None:
        """正常終了時に metrics dict を返すこと"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()

        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("stdout output", "stderr output")
        mock_proc.returncode = 0
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = MagicMock(return_value=False)

        with patch("subprocess.Popen", return_value=mock_proc):
            result = runner.run(image, output_dir, config)

        assert isinstance(result, dict)

    def test_metrics_contains_elapsed_seconds(self, tmp_path: Path) -> None:
        """metrics に elapsed_seconds キーが含まれること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()

        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "")
        mock_proc.returncode = 0
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = MagicMock(return_value=False)

        with patch("subprocess.Popen", return_value=mock_proc):
            result = runner.run(image, output_dir, config)

        assert "elapsed_seconds" in result
        assert isinstance(result["elapsed_seconds"], float)

    def test_elapsed_seconds_is_non_negative(self, tmp_path: Path) -> None:
        """elapsed_seconds が 0 以上であること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()

        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "")
        mock_proc.returncode = 0
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = MagicMock(return_value=False)

        with patch("subprocess.Popen", return_value=mock_proc):
            result = runner.run(image, output_dir, config)

        assert result["elapsed_seconds"] >= 0.0


class TestAudiverisRunnerTimeout:
    """タイムアウト時の動作検証"""

    def test_timeout_raises_omr_timeout_error(self, tmp_path: Path) -> None:
        """TimeoutExpired → OmrTimeoutError に変換されること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path, timeout=5)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()

        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
            cmd="java", timeout=5
        )
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = MagicMock(return_value=False)

        with patch("subprocess.Popen", return_value=mock_proc):
            with pytest.raises(OmrTimeoutError):
                runner.run(image, output_dir, config)

    def test_timeout_kills_process(self, tmp_path: Path) -> None:
        """タイムアウト時に process.kill() が呼ばれること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path, timeout=5)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()

        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
            cmd="java", timeout=5
        )
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = MagicMock(return_value=False)

        with patch("subprocess.Popen", return_value=mock_proc):
            with pytest.raises(OmrTimeoutError):
                runner.run(image, output_dir, config)

        mock_proc.kill.assert_called_once()

    def test_timeout_error_message_contains_timeout_value(
        self, tmp_path: Path
    ) -> None:
        """OmrTimeoutError のメッセージにタイムアウト秒数が含まれること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path, timeout=42)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()

        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
            cmd="java", timeout=42
        )
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = MagicMock(return_value=False)

        with patch("subprocess.Popen", return_value=mock_proc):
            with pytest.raises(OmrTimeoutError, match="42"):
                runner.run(image, output_dir, config)


class TestAudiverisRunnerNonZeroExit:
    """非0 終了コード時の動作検証"""

    def test_nonzero_exit_raises_omr_execution_error(self, tmp_path: Path) -> None:
        """終了コード非0 → OmrExecutionError が raise されること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()

        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (
            "",
            "ERROR: some audiveris failure",
        )
        mock_proc.returncode = 1
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = MagicMock(return_value=False)

        with patch("subprocess.Popen", return_value=mock_proc):
            with pytest.raises(OmrExecutionError):
                runner.run(image, output_dir, config)

    def test_execution_error_contains_stderr(self, tmp_path: Path) -> None:
        """OmrExecutionError のメッセージに stderr が含まれること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()

        stderr_text = "FATAL: Could not open book"
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", stderr_text)
        mock_proc.returncode = 2
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = MagicMock(return_value=False)

        with patch("subprocess.Popen", return_value=mock_proc):
            with pytest.raises(OmrExecutionError, match="FATAL"):
                runner.run(image, output_dir, config)

    def test_execution_error_contains_exit_code(self, tmp_path: Path) -> None:
        """OmrExecutionError のメッセージに終了コードが含まれること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()

        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "some error")
        mock_proc.returncode = 99
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = MagicMock(return_value=False)

        with patch("subprocess.Popen", return_value=mock_proc):
            with pytest.raises(OmrExecutionError, match="99"):
                runner.run(image, output_dir, config)


class TestAudiverisRunnerLogging:
    """stdout/stderr が DEBUG ログに記録されること"""

    def test_stdout_logged_at_debug(self, tmp_path: Path) -> None:
        """stdout が structlog DEBUG ログに記録されること"""
        from pipeline.omr.runner import AudiverisRunner

        config = _make_config(tmp_path)
        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        runner = AudiverisRunner()

        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("Audiveris stdout line", "")
        mock_proc.returncode = 0
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = MagicMock(return_value=False)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch("pipeline.omr.runner.get_logger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger
                runner.run(image, output_dir, config)
                mock_logger.debug.assert_called()

    def test_default_options_class_variable(self, tmp_path: Path) -> None:
        """AudiverisRunner.DEFAULT_OPTIONS が ClassVar として定義されていること"""
        from pipeline.omr.runner import AudiverisRunner

        assert hasattr(AudiverisRunner, "DEFAULT_OPTIONS")
        assert isinstance(AudiverisRunner.DEFAULT_OPTIONS, dict)
        assert len(AudiverisRunner.DEFAULT_OPTIONS) > 0
