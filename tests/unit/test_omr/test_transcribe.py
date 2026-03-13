"""transcribe() ユニットテスト — Task 6: 統合エントリポイント + キャッシュ"""

from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.common import StepResult
from pipeline.omr.config import OmrConfigData
from pipeline.omr.errors import OmrOutputError


def _make_config(tmp_path: Path, timeout: int = 300) -> OmrConfigData:
    jar = tmp_path / "audiveris.jar"
    jar.touch()
    return OmrConfigData(jar_path=jar, timeout_seconds=timeout, extra_options={})


def _create_mxl(mxl_path: Path) -> None:
    valid_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<score-partwise><part-list/></score-partwise>"
    )
    with zipfile.ZipFile(mxl_path, "w") as zf:
        zf.writestr("score.xml", valid_xml)


# ---------------------------------------------------------------------------
# キャッシュヒット
# ---------------------------------------------------------------------------


class TestTranscribeCacheHit:
    """既存 MusicXML がある場合はキャッシュとして扱い再実行しないこと"""

    def test_cache_hit_does_not_call_runner(self, tmp_path: Path) -> None:
        """キャッシュヒット時に runner.run() が呼ばれないこと"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        existing_mxl = output_dir / "score.mxl"
        _create_mxl(existing_mxl)

        config = _make_config(tmp_path)
        mock_runner = MagicMock()

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                result = transcribe(image, output_dir, runner=mock_runner)

        mock_runner.run.assert_not_called()

    def test_cache_hit_returns_cached_true(self, tmp_path: Path) -> None:
        """キャッシュヒット時に metrics['cached'] が True であること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        _create_mxl(output_dir / "score.mxl")

        config = _make_config(tmp_path)
        mock_runner = MagicMock()

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                result = transcribe(image, output_dir, runner=mock_runner)

        assert result.metrics["cached"] is True

    def test_cache_hit_elapsed_seconds_is_zero(self, tmp_path: Path) -> None:
        """キャッシュヒット時に elapsed_seconds が 0.0 であること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        _create_mxl(output_dir / "score.mxl")

        config = _make_config(tmp_path)

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                result = transcribe(image, output_dir)

        assert result.metrics["elapsed_seconds"] == 0.0

    def test_cache_hit_success_is_true(self, tmp_path: Path) -> None:
        """キャッシュヒット時に StepResult.success が True であること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        _create_mxl(output_dir / "score.mxl")

        config = _make_config(tmp_path)

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                result = transcribe(image, output_dir)

        assert result.success is True

    def test_cache_hit_output_path_is_musicxml(self, tmp_path: Path) -> None:
        """キャッシュヒット時に output_path がキャッシュ済み MusicXML パスであること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        existing_mxl = output_dir / "score.mxl"
        _create_mxl(existing_mxl)

        config = _make_config(tmp_path)

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                result = transcribe(image, output_dir)

        assert result.output_path == existing_mxl

    def test_cache_hit_musicxml_path_in_metrics(self, tmp_path: Path) -> None:
        """キャッシュヒット時に metrics['musicxml_path'] が含まれること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        existing_mxl = output_dir / "score.mxl"
        _create_mxl(existing_mxl)

        config = _make_config(tmp_path)

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                result = transcribe(image, output_dir)

        assert "musicxml_path" in result.metrics
        assert result.metrics["musicxml_path"] == str(existing_mxl)


# ---------------------------------------------------------------------------
# キャッシュミス → Audiveris 実行
# ---------------------------------------------------------------------------


class TestTranscribeCacheMiss:
    """キャッシュがない場合はフル処理が実行されること"""

    def test_cache_miss_calls_runner_run(self, tmp_path: Path) -> None:
        """キャッシュミス時に runner.run() が呼ばれること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        config = _make_config(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = {"elapsed_seconds": 12.5}

        found_mxl = output_dir / "score.mxl"
        _create_mxl(found_mxl)

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                with patch(
                    "pipeline.omr._transcribe.MusicXmlFinder.find",
                    side_effect=[OmrOutputError("not found"), found_mxl],
                ):
                    result = transcribe(image, output_dir, runner=mock_runner)

        mock_runner.run.assert_called_once()

    def test_cache_miss_returns_cached_false(self, tmp_path: Path) -> None:
        """キャッシュミス時に metrics['cached'] が False であること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        config = _make_config(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = {"elapsed_seconds": 12.5}

        found_mxl = output_dir / "score.mxl"
        _create_mxl(found_mxl)

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                with patch(
                    "pipeline.omr._transcribe.MusicXmlFinder.find",
                    side_effect=[OmrOutputError("not found"), found_mxl],
                ):
                    result = transcribe(image, output_dir, runner=mock_runner)

        assert result.metrics["cached"] is False

    def test_cache_miss_elapsed_seconds_from_runner(self, tmp_path: Path) -> None:
        """キャッシュミス時の elapsed_seconds が runner.run() の値であること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        config = _make_config(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = {"elapsed_seconds": 42.0}

        found_mxl = output_dir / "score.mxl"
        _create_mxl(found_mxl)

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                with patch(
                    "pipeline.omr._transcribe.MusicXmlFinder.find",
                    side_effect=[OmrOutputError("not found"), found_mxl],
                ):
                    result = transcribe(image, output_dir, runner=mock_runner)

        assert result.metrics["elapsed_seconds"] == 42.0

    def test_cache_miss_success_is_true(self, tmp_path: Path) -> None:
        """キャッシュミス正常実行時に StepResult.success が True であること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        config = _make_config(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = {"elapsed_seconds": 1.0}

        found_mxl = output_dir / "score.mxl"
        _create_mxl(found_mxl)

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                with patch(
                    "pipeline.omr._transcribe.MusicXmlFinder.find",
                    side_effect=[OmrOutputError("not found"), found_mxl],
                ):
                    result = transcribe(image, output_dir, runner=mock_runner)

        assert result.success is True


# ---------------------------------------------------------------------------
# メトリクス検証
# ---------------------------------------------------------------------------


class TestTranscribeMetrics:
    """StepResult.metrics に必要なキーが含まれること"""

    def test_hit_metrics_keys(self, tmp_path: Path) -> None:
        """キャッシュヒット時に cached・elapsed_seconds・musicxml_path が含まれること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        _create_mxl(output_dir / "score.mxl")

        config = _make_config(tmp_path)

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                result = transcribe(image, output_dir)

        assert {"cached", "elapsed_seconds", "musicxml_path"} <= set(result.metrics)

    def test_miss_metrics_keys(self, tmp_path: Path) -> None:
        """キャッシュミス時に cached・elapsed_seconds・musicxml_path が含まれること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        config = _make_config(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = {"elapsed_seconds": 5.0}

        found_mxl = output_dir / "score.mxl"
        _create_mxl(found_mxl)

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                with patch(
                    "pipeline.omr._transcribe.MusicXmlFinder.find",
                    side_effect=[OmrOutputError("not found"), found_mxl],
                ):
                    result = transcribe(image, output_dir, runner=mock_runner)

        assert {"cached", "elapsed_seconds", "musicxml_path"} <= set(result.metrics)

    def test_musicxml_path_is_str(self, tmp_path: Path) -> None:
        """metrics['musicxml_path'] が文字列であること"""
        from pipeline.omr._transcribe import transcribe

        image = tmp_path / "score.png"
        image.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        _create_mxl(output_dir / "score.mxl")

        config = _make_config(tmp_path)

        with patch("pipeline.omr._transcribe.OmrConfig.load", return_value=config):
            with patch("pipeline.omr._transcribe.OmrEngine.validate_environment"):
                result = transcribe(image, output_dir)

        assert isinstance(result.metrics["musicxml_path"], str)


# ---------------------------------------------------------------------------
# __init__.py re-export
# ---------------------------------------------------------------------------


class TestTranscribePublicApi:
    """pipeline.omr から直接 transcribe() を import できること"""

    def test_transcribe_importable_from_omr_package(self) -> None:
        """pipeline.omr.transcribe が import できること"""
        from pipeline.omr import transcribe

        assert callable(transcribe)
