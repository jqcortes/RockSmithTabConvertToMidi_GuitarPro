"""
tests/unit/test_omr/test_errors.py — OmrError 継承階層のユニットテスト

Task 7.1 対応。
TDD RED フェーズ: pipeline.omr.errors が存在しない段階で失敗することを確認する。
"""

import pytest

from pipeline.common import PipelineError


class TestOmrErrorHierarchy:
    """OmrError が PipelineError を継承していること"""

    def test_omr_error_is_pipeline_error(self) -> None:
        from pipeline.omr.errors import OmrError

        assert issubclass(OmrError, PipelineError)

    def test_omr_error_is_exception(self) -> None:
        from pipeline.omr.errors import OmrError

        assert issubclass(OmrError, Exception)

    def test_omr_error_can_be_raised_and_caught_as_pipeline_error(self) -> None:
        from pipeline.omr.errors import OmrError

        with pytest.raises(PipelineError):
            raise OmrError("test")

    def test_omr_error_message_preserved(self) -> None:
        from pipeline.omr.errors import OmrError

        err = OmrError("something went wrong")
        assert "something went wrong" in str(err)


class TestOmrErrorSubclasses:
    """4 種のサブクラスが OmrError を継承していること"""

    def test_environment_error_is_omr_error(self) -> None:
        from pipeline.omr.errors import OmrEnvironmentError, OmrError

        assert issubclass(OmrEnvironmentError, OmrError)

    def test_timeout_error_is_omr_error(self) -> None:
        from pipeline.omr.errors import OmrError, OmrTimeoutError

        assert issubclass(OmrTimeoutError, OmrError)

    def test_execution_error_is_omr_error(self) -> None:
        from pipeline.omr.errors import OmrError, OmrExecutionError

        assert issubclass(OmrExecutionError, OmrError)

    def test_output_error_is_omr_error(self) -> None:
        from pipeline.omr.errors import OmrError, OmrOutputError

        assert issubclass(OmrOutputError, OmrError)

    def test_all_subclasses_are_pipeline_errors(self) -> None:
        from pipeline.omr.errors import (
            OmrEnvironmentError,
            OmrExecutionError,
            OmrOutputError,
            OmrTimeoutError,
        )

        for cls in (OmrEnvironmentError, OmrTimeoutError, OmrExecutionError, OmrOutputError):
            assert issubclass(cls, PipelineError), f"{cls.__name__} は PipelineError のサブクラスであること"

    def test_environment_error_can_be_raised(self) -> None:
        from pipeline.omr.errors import OmrEnvironmentError

        with pytest.raises(OmrEnvironmentError, match="Java 17"):
            raise OmrEnvironmentError("Java 17+ が必要です")

    def test_timeout_error_can_be_raised(self) -> None:
        from pipeline.omr.errors import OmrTimeoutError

        with pytest.raises(OmrTimeoutError):
            raise OmrTimeoutError("Audiveris タイムアウト")

    def test_execution_error_can_be_raised(self) -> None:
        from pipeline.omr.errors import OmrExecutionError

        with pytest.raises(OmrExecutionError):
            raise OmrExecutionError("終了コード 1: ...")

    def test_output_error_can_be_raised(self) -> None:
        from pipeline.omr.errors import OmrOutputError

        with pytest.raises(OmrOutputError):
            raise OmrOutputError("MusicXML が生成されませんでした")


class TestOmrErrorSelectiveCatch:
    """サブクラスを選択的にキャッチできること"""

    def test_catch_specific_subclass(self) -> None:
        from pipeline.omr.errors import OmrError, OmrTimeoutError

        caught_specific = False
        try:
            raise OmrTimeoutError("timeout")
        except OmrTimeoutError:
            caught_specific = True

        assert caught_specific

    def test_parent_catch_catches_child(self) -> None:
        from pipeline.omr.errors import OmrEnvironmentError, OmrError

        caught_as_parent = False
        try:
            raise OmrEnvironmentError("env error")
        except OmrError:
            caught_as_parent = True

        assert caught_as_parent

    def test_subclasses_are_independent(self) -> None:
        """OmrTimeoutError が OmrExecutionError として捕まえられないこと"""
        from pipeline.omr.errors import OmrExecutionError, OmrTimeoutError

        with pytest.raises(OmrTimeoutError):
            try:
                raise OmrTimeoutError("timeout")
            except OmrExecutionError:
                pass  # ここには来ない
