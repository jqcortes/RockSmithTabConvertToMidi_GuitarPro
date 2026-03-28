"""tests for TransformError hierarchy."""

import pytest

from pipeline.common import PipelineError


class TestTransformErrorHierarchy:
    """Task 1.1 RED tests for transform errors."""

    def test_transform_error_is_pipeline_error(self) -> None:
        from pipeline.transform.errors import TransformError

        assert issubclass(TransformError, PipelineError)

    def test_transform_subclasses_inherit_transform_error(self) -> None:
        from pipeline.transform.errors import (
            TransformError,
            TransformGuitarFixerError,
            TransformPartError,
            TransformTabOcrError,
            TransformValidationError,
        )

        assert issubclass(TransformValidationError, TransformError)
        assert issubclass(TransformGuitarFixerError, TransformError)
        assert issubclass(TransformTabOcrError, TransformError)
        assert issubclass(TransformPartError, TransformError)


class TestTransformErrorBehavior:
    """Task 1.2 tests for transform error behavior."""

    @pytest.mark.parametrize(
        ("error_type", "message"),
        [
            ("TransformError", "transform failed"),
            ("TransformValidationError", "invalid musicxml"),
            ("TransformGuitarFixerError", "guitar fixer failed"),
            ("TransformTabOcrError", "tab ocr failed"),
            ("TransformPartError", "part identification failed"),
        ],
    )
    def test_errors_can_be_caught_as_pipeline_error(
        self,
        error_type: str,
        message: str,
    ) -> None:
        from pipeline.transform import errors

        error_class = getattr(errors, error_type)

        with pytest.raises(PipelineError, match=message):
            raise error_class(message)

    @pytest.mark.parametrize(
        ("error_type", "message"),
        [
            ("TransformError", "transform failed"),
            ("TransformValidationError", "invalid musicxml"),
            ("TransformGuitarFixerError", "guitar fixer failed"),
            ("TransformTabOcrError", "tab ocr failed"),
            ("TransformPartError", "part identification failed"),
        ],
    )
    def test_error_messages_are_preserved(self, error_type: str, message: str) -> None:
        from pipeline.transform import errors

        error_class = getattr(errors, error_type)
        error = error_class(message)

        assert str(error) == message
