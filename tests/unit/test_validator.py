"""
Unit tests for pipeline/ingest/validator.py — TDD: RED phase

Task 4 scope:
- validate(image_path: Path) -> StepResult
- PIL.Image.info.get("dpi") で解像度を取得（デフォルト 72dpi）
- 解像度 < 200dpi → IngestError("Resolution {dpi}dpi below minimum 200dpi")
- 200dpi ≤ 解像度 < 300dpi → warnings: "Low resolution: {dpi}dpi (recommended: 300dpi+)"
- 解像度 ≥ 300dpi → 警告なし
- 黒画素比率 < 5% or > 40% → warnings: "Unusual black pixel ratio: {ratio:.1%}"
- StepResult.output_path = 入力 image_path（変換なし）
- StepResult.metrics = {"dpi": float, "black_pixel_ratio": float}
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_png(tmp_path: Path, dpi: tuple[float, float], black_ratio: float) -> Path:
    """指定した DPI メタデータと黒画素比率で PNG を作成して返す。

    black_ratio: 0.0〜1.0
    """
    size = 100
    total_px = size * size
    black_px = int(total_px * black_ratio)
    arr = np.full((size, size), 255, dtype=np.uint8)
    if black_px > 0:
        # 先頭から black_px 個を 0 にする
        flat = arr.flatten()
        flat[:black_px] = 0
        arr = flat.reshape(size, size)

    p = tmp_path / f"img_{dpi[0]}dpi_{black_ratio:.0%}.png"
    img = Image.fromarray(arr, mode="L")
    img.save(p, dpi=dpi)
    return p


@pytest.fixture()
def high_dpi_normal_ratio(tmp_path: Path) -> Path:
    """300dpi・黒画素比率 24%（正常）"""
    return _make_png(tmp_path, dpi=(300.0, 300.0), black_ratio=0.24)


@pytest.fixture()
def mid_dpi_normal_ratio(tmp_path: Path) -> Path:
    """250dpi・黒画素比率 24%（低解像度警告）"""
    return _make_png(tmp_path, dpi=(250.0, 250.0), black_ratio=0.24)


@pytest.fixture()
def low_dpi_normal_ratio(tmp_path: Path) -> Path:
    """150dpi・黒画素比率 24%（解像度エラー）"""
    return _make_png(tmp_path, dpi=(150.0, 150.0), black_ratio=0.24)


@pytest.fixture()
def high_dpi_low_ratio(tmp_path: Path) -> Path:
    """300dpi・黒画素比率 1%（黒画素低比率警告）"""
    return _make_png(tmp_path, dpi=(300.0, 300.0), black_ratio=0.01)


@pytest.fixture()
def high_dpi_high_ratio(tmp_path: Path) -> Path:
    """300dpi・黒画素比率 90%（黒画素高比率警告）"""
    return _make_png(tmp_path, dpi=(300.0, 300.0), black_ratio=0.90)


# ---------------------------------------------------------------------------
# validate() — 基本動作テスト
# ---------------------------------------------------------------------------


class TestValidatorBasic:
    def test_validate_returns_stepresult(
        self, high_dpi_normal_ratio: Path
    ) -> None:
        """validate() が StepResult を返すこと"""
        from pipeline.common import StepResult
        from pipeline.ingest.validator import validate

        assert isinstance(validate(high_dpi_normal_ratio), StepResult)

    def test_validate_success_true_for_valid_image(
        self, high_dpi_normal_ratio: Path
    ) -> None:
        """正常画像で success=True であること"""
        from pipeline.ingest.validator import validate

        assert validate(high_dpi_normal_ratio).success is True

    def test_validate_output_path_is_input_path(
        self, high_dpi_normal_ratio: Path
    ) -> None:
        """output_path が入力パスをそのまま返すこと（変換なし）"""
        from pipeline.ingest.validator import validate

        result = validate(high_dpi_normal_ratio)
        assert result.output_path == high_dpi_normal_ratio

    def test_validate_no_warnings_for_good_image(
        self, high_dpi_normal_ratio: Path
    ) -> None:
        """解像度 ≥ 300dpi・比率 5〜40% の場合は warnings が空であること"""
        from pipeline.ingest.validator import validate

        result = validate(high_dpi_normal_ratio)
        assert result.warnings == []


# ---------------------------------------------------------------------------
# validate() — metrics テスト
# ---------------------------------------------------------------------------


class TestValidatorMetrics:
    def test_metrics_contains_dpi(self, high_dpi_normal_ratio: Path) -> None:
        """metrics に dpi キーが含まれること"""
        from pipeline.ingest.validator import validate

        assert "dpi" in validate(high_dpi_normal_ratio).metrics

    def test_metrics_contains_black_pixel_ratio(
        self, high_dpi_normal_ratio: Path
    ) -> None:
        """metrics に black_pixel_ratio キーが含まれること"""
        from pipeline.ingest.validator import validate

        assert "black_pixel_ratio" in validate(high_dpi_normal_ratio).metrics

    def test_metrics_dpi_is_float(self, high_dpi_normal_ratio: Path) -> None:
        """metrics["dpi"] が float であること"""
        from pipeline.ingest.validator import validate

        dpi = validate(high_dpi_normal_ratio).metrics["dpi"]
        assert isinstance(dpi, float)

    def test_metrics_dpi_value_matches_image(self, high_dpi_normal_ratio: Path) -> None:
        """metrics["dpi"] が画像の DPI と一致すること（300dpi）"""
        from pipeline.ingest.validator import validate

        dpi = float(validate(high_dpi_normal_ratio).metrics["dpi"])
        assert dpi == pytest.approx(300.0, abs=1.0)

    def test_metrics_black_pixel_ratio_in_range(
        self, high_dpi_normal_ratio: Path
    ) -> None:
        """metrics["black_pixel_ratio"] が 0.0〜1.0 の範囲内であること"""
        from pipeline.ingest.validator import validate

        ratio = float(validate(high_dpi_normal_ratio).metrics["black_pixel_ratio"])
        assert 0.0 <= ratio <= 1.0


# ---------------------------------------------------------------------------
# validate() — 解像度ゲートテスト
# ---------------------------------------------------------------------------


class TestValidatorResolution:
    def test_low_dpi_raises_ingest_error(self, low_dpi_normal_ratio: Path) -> None:
        """解像度 < 200dpi で IngestError が raise されること"""
        from pipeline.common import IngestError
        from pipeline.ingest.validator import validate

        with pytest.raises(IngestError):
            validate(low_dpi_normal_ratio)

    def test_low_dpi_error_message_contains_dpi(
        self, low_dpi_normal_ratio: Path
    ) -> None:
        """エラーメッセージに DPI 値が含まれること"""
        from pipeline.common import IngestError
        from pipeline.ingest.validator import validate

        with pytest.raises(IngestError, match="150"):
            validate(low_dpi_normal_ratio)

    def test_low_dpi_error_message_contains_minimum(
        self, low_dpi_normal_ratio: Path
    ) -> None:
        """エラーメッセージに 'minimum' または '200' が含まれること"""
        from pipeline.common import IngestError
        from pipeline.ingest.validator import validate

        with pytest.raises(IngestError, match=r"200"):
            validate(low_dpi_normal_ratio)

    def test_mid_dpi_adds_low_resolution_warning(
        self, mid_dpi_normal_ratio: Path
    ) -> None:
        """200dpi ≤ 解像度 < 300dpi のとき warnings に低解像度メッセージが追加されること"""
        from pipeline.ingest.validator import validate

        result = validate(mid_dpi_normal_ratio)
        low_res_warns = [w for w in result.warnings if "resolution" in w.lower()]
        assert len(low_res_warns) >= 1

    def test_mid_dpi_warning_contains_dpi_value(
        self, mid_dpi_normal_ratio: Path
    ) -> None:
        """低解像度警告メッセージに DPI 値が含まれること"""
        from pipeline.ingest.validator import validate

        result = validate(mid_dpi_normal_ratio)
        low_res_warns = [w for w in result.warnings if "resolution" in w.lower()]
        assert "250" in low_res_warns[0]

    def test_mid_dpi_success_is_true(self, mid_dpi_normal_ratio: Path) -> None:
        """200〜299dpi の場合は警告はあるが success=True であること"""
        from pipeline.ingest.validator import validate

        result = validate(mid_dpi_normal_ratio)
        assert result.success is True

    def test_300dpi_no_resolution_warning(self, high_dpi_normal_ratio: Path) -> None:
        """300dpi の場合は解像度警告がないこと"""
        from pipeline.ingest.validator import validate

        result = validate(high_dpi_normal_ratio)
        low_res_warns = [w for w in result.warnings if "resolution" in w.lower()]
        assert len(low_res_warns) == 0

    def test_default_dpi_72_raises_ingest_error(self, tmp_path: Path) -> None:
        """DPI メタデータなし（デフォルト 72dpi）の画像で IngestError が raise されること"""
        from pipeline.common import IngestError
        from pipeline.ingest.validator import validate

        # DPI メタデータなしで保存（PIL デフォルト 72dpi 扱い）
        arr = np.full((100, 100), 255, dtype=np.uint8)
        no_dpi_png = tmp_path / "no_dpi.png"
        Image.fromarray(arr, mode="L").save(no_dpi_png)  # dpi 引数なし

        with pytest.raises(IngestError):
            validate(no_dpi_png)

    def test_validate_uses_custom_minimum_dpi(self, low_dpi_normal_ratio: Path) -> None:
        """カスタム minimum_dpi を下げると低 DPI 画像でも通ること"""
        from pipeline.ingest.validator import validate

        result = validate(low_dpi_normal_ratio, minimum_dpi=150.0, recommended_dpi=250.0)

        assert result.success is True

    def test_validate_uses_custom_recommended_dpi(self, mid_dpi_normal_ratio: Path) -> None:
        """カスタム recommended_dpi を下げると警告閾値も下がること"""
        from pipeline.ingest.validator import validate

        result = validate(mid_dpi_normal_ratio, minimum_dpi=200.0, recommended_dpi=240.0)

        low_res_warns = [w for w in result.warnings if "resolution" in w.lower()]
        assert low_res_warns == []


# ---------------------------------------------------------------------------
# validate() — 黒画素比率警告テスト
# ---------------------------------------------------------------------------


class TestValidatorBlackPixelRatio:
    def test_low_black_ratio_adds_warning(self, high_dpi_low_ratio: Path) -> None:
        """黒画素比率 < 5% のとき warnings に品質メッセージが追加されること"""
        from pipeline.ingest.validator import validate

        result = validate(high_dpi_low_ratio)
        ratio_warns = [w for w in result.warnings if "black pixel" in w.lower()]
        assert len(ratio_warns) >= 1

    def test_high_black_ratio_adds_warning(self, high_dpi_high_ratio: Path) -> None:
        """黒画素比率 > 40% のとき warnings に品質メッセージが追加されること"""
        from pipeline.ingest.validator import validate

        result = validate(high_dpi_high_ratio)
        ratio_warns = [w for w in result.warnings if "black pixel" in w.lower()]
        assert len(ratio_warns) >= 1

    def test_black_ratio_warning_contains_percentage(
        self, high_dpi_low_ratio: Path
    ) -> None:
        """黒画素比率警告メッセージに % 表記の数値が含まれること"""
        from pipeline.ingest.validator import validate

        result = validate(high_dpi_low_ratio)
        ratio_warns = [w for w in result.warnings if "black pixel" in w.lower()]
        assert "%" in ratio_warns[0]

    def test_normal_ratio_no_black_pixel_warning(
        self, high_dpi_normal_ratio: Path
    ) -> None:
        """黒画素比率が 5〜40% の場合は黒画素警告なしであること"""
        from pipeline.ingest.validator import validate

        result = validate(high_dpi_normal_ratio)
        ratio_warns = [w for w in result.warnings if "black pixel" in w.lower()]
        assert len(ratio_warns) == 0
