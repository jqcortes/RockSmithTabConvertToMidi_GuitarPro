"""pipeline.transform.errors - Transform domain exception hierarchy."""

from __future__ import annotations

from pipeline.common import PipelineError


class TransformError(PipelineError):
    """Transform ドメイン全般の基底例外。"""


class TransformValidationError(TransformError):
    """MusicXML 入力の妥当性検証に失敗した場合の例外。"""


class TransformGuitarFixerError(TransformError):
    """TAB 補正処理で失敗した場合の例外。"""


class TransformTabOcrError(TransformError):
    """TAB OCR 補完処理で失敗した場合の例外。"""


class TransformPartError(TransformError):
    """パート識別処理で失敗した場合の例外。"""
