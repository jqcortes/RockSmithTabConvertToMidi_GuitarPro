"""pipeline.quality.errors - Quality domain exception hierarchy."""

from __future__ import annotations

from pipeline.common import PipelineError


class QualityError(PipelineError):
    """Quality ドメイン全般の基底例外。"""


class QualityValidationError(QualityError):
    """Quality 入力の妥当性検証に失敗した場合の例外。"""


class QualityExecutionError(QualityError):
    """品質スコア算出またはレポート出力に失敗した場合の例外。"""