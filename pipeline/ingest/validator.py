"""
pipeline/ingest/validator.py — 入力画像の解像度・品質バリデーション

Audiveris に渡す前に画像が最低品質基準を満たしているか確認する。

検証ルール:
  - 解像度 < 200dpi        → IngestError (処理不可)
  - 200dpi ≤ 解像度 < 300dpi → warnings (低品質警告)
  - 解像度 ≥ 300dpi        → 正常
  - 黒画素比率 < 5% or > 40% → warnings (品質警告)

Public API:
    validate(image_path) -> StepResult
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from pipeline.common import IngestError, MetricValue, StepResult, get_logger

_log = get_logger(__name__)

# 解像度閾値定数
_DPI_MINIMUM: float = 200.0
_DPI_RECOMMENDED: float = 300.0
_DPI_DEFAULT: float = 72.0  # PIL が DPI メタデータなし時に返す値

# 黒画素比率の正常範囲
_BLACK_RATIO_MIN: float = 0.05
_BLACK_RATIO_MAX: float = 0.40


def validate(
    image_path: Path,
    *,
    minimum_dpi: float = _DPI_MINIMUM,
    recommended_dpi: float = _DPI_RECOMMENDED,
) -> StepResult:
    """画像の解像度と黒画素比率を検証して StepResult を返す。

    画像自体は変換しない（output_path = image_path）。

    Args:
        image_path: 検証対象の PNG / JPEG / TIFF ファイルパス

    Returns:
        StepResult:
            output_path — 入力 image_path をそのまま返す
            metrics     — {"dpi": float, "black_pixel_ratio": float}
            warnings    — 非致命的な品質警告のリスト

    Raises:
        IngestError: 解像度が _DPI_MINIMUM 未満の場合
    """
    warnings: list[str] = []
    metrics: dict[str, MetricValue] = {}

    # ---- DPI 取得 ----
    with Image.open(image_path) as pil_img:
        raw_dpi = pil_img.info.get("dpi", (_DPI_DEFAULT, _DPI_DEFAULT))
        # 短辺方向の DPI を使用（横長・縦長どちらでも低い方が基準）
        # PIL の浮動小数点誤差（300.0 → 299.9994 等）を吸収するため round する
        dpi = float(round(min(raw_dpi[0], raw_dpi[1])))

        # ---- 黒画素比率計算（PNG に変換して numpy で計算）----
        gray = pil_img.convert("L")
        arr = np.array(gray)

    black_ratio = float(np.sum(arr < 128)) / float(arr.size)
    metrics["dpi"] = dpi
    metrics["black_pixel_ratio"] = black_ratio

    # ---- 解像度ゲート ----
    if dpi < minimum_dpi:
        raise IngestError(
            f"Resolution {dpi:.0f}dpi below minimum {minimum_dpi:.0f}dpi"
        )

    if dpi < recommended_dpi:
        warnings.append(
            f"Low resolution: {dpi:.0f}dpi (recommended: {recommended_dpi:.0f}dpi+)"
        )

    # ---- 黒画素比率チェック ----
    if black_ratio < _BLACK_RATIO_MIN or black_ratio > _BLACK_RATIO_MAX:
        warnings.append(
            f"Unusual black pixel ratio: {black_ratio:.1%}"
        )

    _log.info(
        "validate_done",
        path=str(image_path),
        dpi=dpi,
        black_pixel_ratio=f"{black_ratio:.1%}",
        warnings=len(warnings),
    )
    return StepResult.ok(image_path, metrics=metrics, warnings=warnings)
