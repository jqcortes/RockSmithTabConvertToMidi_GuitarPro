"""tests for RenderError hierarchy."""

import pytest

from pipeline.common import PipelineError


class TestRenderErrorHierarchy:
    """Task 1.1 RED tests for render errors."""

    def test_render_error_is_pipeline_error(self) -> None:
        from pipeline.render.errors import RenderError

        assert issubclass(RenderError, PipelineError)

    def test_render_subclasses_inherit_render_error(self) -> None:
        from pipeline.render.errors import (
            RenderError,
            RenderExecutionError,
            RenderValidationError,
        )

        assert issubclass(RenderValidationError, RenderError)
        assert issubclass(RenderExecutionError, RenderError)


class TestRenderErrorBehavior:
    """Task 1.1 behavior tests for render errors."""

    @pytest.mark.parametrize(
        ("error_type", "message"),
        [
            ("RenderError", "render failed"),
            ("RenderValidationError", "invalid musicxml"),
            ("RenderExecutionError", "midi write failed"),
        ],
    )
    def test_errors_can_be_caught_as_pipeline_error(
        self,
        error_type: str,
        message: str,
    ) -> None:
        from pipeline.render import errors

        error_class = getattr(errors, error_type)

        with pytest.raises(PipelineError, match=message):
            raise error_class(message)

    @pytest.mark.parametrize(
        ("error_type", "message"),
        [
            ("RenderError", "render failed"),
            ("RenderValidationError", "invalid musicxml"),
            ("RenderExecutionError", "midi write failed"),
        ],
    )
    def test_error_messages_are_preserved(self, error_type: str, message: str) -> None:
        from pipeline.render import errors

        error_class = getattr(errors, error_type)
        error = error_class(message)

        assert str(error) == message