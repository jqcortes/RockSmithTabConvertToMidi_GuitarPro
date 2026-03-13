"""pipeline.render.errors - Render domain exception hierarchy."""

from __future__ import annotations

from pipeline.common import PipelineError


class RenderError(PipelineError):
    """Render ドメイン全般の基底例外。"""


class RenderValidationError(RenderError):
    """MusicXML 入力の妥当性検証に失敗した場合の例外。"""


class RenderExecutionError(RenderError):
    """MIDI 生成または書き出し処理で失敗した場合の例外。"""