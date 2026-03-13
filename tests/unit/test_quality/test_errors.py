"""tests for QualityError hierarchy."""

import pytest

from pipeline.common import PipelineError


class TestQualityErrorHierarchy:
    """Task 1.1 RED tests for quality errors."""

    def test_quality_error_is_pipeline_error(self) -> None:
        from pipeline.quality.errors import QualityError

        assert issubclass(QualityError, PipelineError)

    def test_quality_subclasses_inherit_quality_error(self) -> None:
        from pipeline.quality.errors import (
            QualityError,
            QualityExecutionError,
            QualityValidationError,
        )

        assert issubclass(QualityValidationError, QualityError)
        assert issubclass(QualityExecutionError, QualityError)


class TestQualityErrorBehavior:
    """Task 1.1 behavior tests for quality errors."""

    @pytest.mark.parametrize(
        ("error_type", "message"),
        [
            ("QualityError", "quality failed"),
            ("QualityValidationError", "invalid quality input"),
            ("QualityExecutionError", "quality report write failed"),
        ],
    )
    def test_errors_can_be_caught_as_pipeline_error(
        self,
        error_type: str,
        message: str,
    ) -> None:
        from pipeline.quality import errors

        error_class = getattr(errors, error_type)

        with pytest.raises(PipelineError, match=message):
            raise error_class(message)

    @pytest.mark.parametrize(
        ("error_type", "message"),
        [
            ("QualityError", "quality failed"),
            ("QualityValidationError", "invalid quality input"),
            ("QualityExecutionError", "quality report write failed"),
        ],
    )
    def test_error_messages_are_preserved(self, error_type: str, message: str) -> None:
        from pipeline.quality import errors

        error_class = getattr(errors, error_type)
        error = error_class(message)

        assert str(error) == message