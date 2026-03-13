"""
Unit tests for pipeline/common.py — TDD: RED phase

Task 1 scope:
- StepResult dataclass (success, output_path, metrics, warnings)
- StepResult.ok() factory method
- PipelineError base exception
- IngestError subclass
- structlog logger retrieved without error
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestStepResult:
    """StepResult dataclass のテスト群"""

    def test_stepresult_fields_required(self) -> None:
        """全フィールドが必須と期待値で格納されること"""
        from pipeline.common import StepResult

        result = StepResult(
            success=True,
            output_path=Path("/tmp/out.png"),
            metrics={"page_count": 1},
            warnings=[],
        )

        assert result.success is True
        assert result.output_path == Path("/tmp/out.png")
        assert result.metrics == {"page_count": 1}
        assert result.warnings == []

    def test_stepresult_output_path_can_be_list(self) -> None:
        """output_path が list[Path] でも格納できること"""
        from pipeline.common import StepResult

        pages = [Path("/tmp/p001.png"), Path("/tmp/p002.png")]
        result = StepResult(
            success=True,
            output_path=pages,
            metrics={"page_count": 2},
            warnings=[],
        )

        assert result.output_path == pages

    def test_stepresult_ok_factory_creates_success_result(self) -> None:
        """StepResult.ok() が success=True の結果を返すこと"""
        from pipeline.common import StepResult

        path = Path("/tmp/out.png")
        result = StepResult.ok(path)

        assert result.success is True
        assert result.output_path == path
        assert isinstance(result.metrics, dict)
        assert isinstance(result.warnings, list)

    def test_stepresult_ok_factory_accepts_metrics(self) -> None:
        """StepResult.ok() が metrics キーワード引数を受け取ること"""
        from pipeline.common import StepResult

        result = StepResult.ok(
            Path("/tmp/out.png"),
            metrics={"page_count": 3, "cached": True},
        )

        assert result.metrics["page_count"] == 3
        assert result.metrics["cached"] is True

    def test_stepresult_ok_factory_accepts_warnings(self) -> None:
        """StepResult.ok() が warnings キーワード引数を受け取ること"""
        from pipeline.common import StepResult

        result = StepResult.ok(
            Path("/tmp/out.png"),
            warnings=["Low resolution: 250dpi"],
        )

        assert "Low resolution: 250dpi" in result.warnings

    def test_stepresult_ok_factory_with_list_path(self) -> None:
        """StepResult.ok() が list[Path] を output_path として受け取ること"""
        from pipeline.common import StepResult

        pages = [Path("/tmp/p001.png")]
        result = StepResult.ok(pages)

        assert result.output_path == pages

    def test_stepresult_default_metrics_is_empty_dict(self) -> None:
        """StepResult.ok() のデフォルト metrics が空 dict であること"""
        from pipeline.common import StepResult

        result = StepResult.ok(Path("/tmp/out.png"))

        assert result.metrics == {}

    def test_stepresult_default_warnings_is_empty_list(self) -> None:
        """StepResult.ok() のデフォルト warnings が空 list であること"""
        from pipeline.common import StepResult

        result = StepResult.ok(Path("/tmp/out.png"))

        assert result.warnings == []


class TestPipelineError:
    """PipelineError 基底例外のテスト群"""

    def test_pipeline_error_is_exception(self) -> None:
        """PipelineError が Exception のサブクラスであること"""
        from pipeline.common import PipelineError

        assert issubclass(PipelineError, Exception)

    def test_pipeline_error_can_be_raised_and_caught(self) -> None:
        """PipelineError が raise/catch できること"""
        from pipeline.common import PipelineError

        with pytest.raises(PipelineError, match="test error"):
            raise PipelineError("test error")

    def test_pipeline_error_stores_message(self) -> None:
        """PipelineError がメッセージを保持すること"""
        from pipeline.common import PipelineError

        err = PipelineError("something went wrong")
        assert str(err) == "something went wrong"


class TestIngestError:
    """IngestError のテスト群"""

    def test_ingest_error_is_pipeline_error(self) -> None:
        """IngestError が PipelineError のサブクラスであること"""
        from pipeline.common import IngestError, PipelineError

        assert issubclass(IngestError, PipelineError)

    def test_ingest_error_is_exception(self) -> None:
        """IngestError が Exception として catch できること"""
        from pipeline.common import IngestError

        with pytest.raises(Exception):
            raise IngestError("ingest failed")

    def test_ingest_error_caught_as_pipeline_error(self) -> None:
        """IngestError が PipelineError として catch できること（LSP 準拠）"""
        from pipeline.common import IngestError, PipelineError

        with pytest.raises(PipelineError):
            raise IngestError("file not found: /path/to/file.pdf")

    def test_ingest_error_stores_message(self) -> None:
        """IngestError がメッセージを保持すること"""
        from pipeline.common import IngestError

        err = IngestError("Unsupported format: .docx")
        assert "Unsupported format: .docx" in str(err)


class TestLogger:
    """structlog ロガー取得のテスト群"""

    def test_get_logger_returns_logger(self) -> None:
        """get_logger() が None でないロガーオブジェクトを返すこと"""
        from pipeline.common import get_logger

        logger = get_logger(__name__)
        assert logger is not None

    def test_get_logger_can_bind(self) -> None:
        """get_logger() の戻り値が bind() メソッドを持つこと（structlog BoundLogger）"""
        from pipeline.common import get_logger

        logger = get_logger(__name__)
        bound = logger.bind(component="test")
        assert bound is not None
