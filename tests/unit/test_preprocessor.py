"""
Unit tests for pipeline/ingest/preprocessor.py — TDD: RED phase

Task 3 scope:
- preprocess(image_path, output_dir) -> StepResult
- グレースケール変換
- HoughLinesP によるデスキュー（±10° 以内のみ補正、超過は warnings）
- Otsu 二値化
- CLAHE コントラスト正規化
- 余白トリミング
- 黒画素比率 5〜40% 範囲外 → StepResult.warnings
- metrics: skew_angle, binarization_threshold, black_pixel_ratio
- output_path = Path (単一ファイル)
"""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def score_png(tmp_path: Path) -> Path:
    """楽譜スタッフライン風 PNG (100×100)。

    コンテンツ領域（rows 25-45, cols 10-89 = 21×80 = 1680px）に 5 本の水平線。
    黒画素: 5 本 × 80 = 400 画素 / 1680 画素 ≈ 23.8%（トリミング後）
    """
    arr = np.full((100, 100), 255, dtype=np.uint8)
    for y in [25, 30, 35, 40, 45]:
        arr[y, 10:90] = 0  # 1px 厭スタッフライン
    p = tmp_path / "score.png"
    Image.fromarray(arr, mode="L").save(p)
    return p


@pytest.fixture()
def gray_png(tmp_path: Path) -> Path:
    """スタッフライン PNG（score_png の別名）"""
    arr = np.full((100, 100), 255, dtype=np.uint8)
    for y in [25, 30, 35, 40, 45]:
        arr[y, 10:90] = 0
    p = tmp_path / "score.png"
    Image.fromarray(arr, mode="L").save(p)
    return p


@pytest.fixture()
def white_png(tmp_path: Path) -> Path:
    """真っ白な PNG（黒画素比率 0% — 低比率警告ケース）"""
    p = tmp_path / "white.png"
    Image.fromarray(np.full((100, 100), 255, dtype=np.uint8), mode="L").save(p)
    return p


@pytest.fixture()
def black_png(tmp_path: Path) -> Path:
    """真っ黒な PNG（黒画素比率 100% — 高比率警告ケース）"""
    p = tmp_path / "black.png"
    Image.fromarray(np.zeros((100, 100), dtype=np.uint8), mode="L").save(p)
    return p


@pytest.fixture()
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "preprocess_out"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# preprocess() — 基本動作テスト
# ---------------------------------------------------------------------------


class TestPreprocessorBasic:
    """preprocess() の基本動作テスト群"""

    def test_preprocess_returns_stepresult(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """StepResult が返ること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)

        from pipeline.common import StepResult
        assert isinstance(result, StepResult)

    def test_preprocess_success_is_true(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """正常完了時に success=True であること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)
        assert result.success is True

    def test_preprocess_output_path_is_single_file(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """output_path が list ではなく Path であること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)
        assert isinstance(result.output_path, Path)

    def test_preprocess_output_file_exists(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """output_path のファイルが実際に存在すること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)
        assert result.output_path.exists()  # type: ignore[union-attr]

    def test_preprocess_output_is_png(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """出力ファイルの拡張子が .png であること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)
        assert result.output_path.suffix == ".png"  # type: ignore[union-attr]

    def test_preprocess_creates_output_dir_if_not_exists(
        self, gray_png: Path, tmp_path: Path
    ) -> None:
        """output_dir が存在しない場合は自動作成すること"""
        from pipeline.ingest.preprocessor import preprocess

        new_dir = tmp_path / "new" / "subdir"
        assert not new_dir.exists()

        preprocess(gray_png, output_dir=new_dir)
        assert new_dir.exists()

    def test_preprocess_preserves_source_dpi_metadata(
        self, tmp_path: Path, output_dir: Path
    ) -> None:
        """前処理後の PNG に元画像の DPI が引き継がれること"""
        from pipeline.ingest.preprocessor import preprocess

        arr = np.full((100, 100), 255, dtype=np.uint8)
        for y in [25, 30, 35, 40, 45]:
            arr[y, 10:90] = 0

        source_path = tmp_path / "dpi_source.png"
        Image.fromarray(arr, mode="L").save(source_path, dpi=(300, 300))

        result = preprocess(source_path, output_dir=output_dir)

        with Image.open(result.output_path) as saved_image:  # type: ignore[arg-type]
            saved_dpi = saved_image.info.get("dpi")

        assert saved_dpi is not None
        assert round(min(saved_dpi[0], saved_dpi[1])) == 300


# ---------------------------------------------------------------------------
# preprocess() — metrics テスト
# ---------------------------------------------------------------------------


class TestPreprocessorMetrics:
    """metrics の内容テスト群"""

    def test_metrics_contains_skew_angle(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """metrics に skew_angle キーが含まれること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)
        assert "skew_angle" in result.metrics

    def test_metrics_contains_binarization_threshold(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """metrics に binarization_threshold キーが含まれること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)
        assert "binarization_threshold" in result.metrics

    def test_metrics_contains_black_pixel_ratio(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """metrics に black_pixel_ratio キーが含まれること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)
        assert "black_pixel_ratio" in result.metrics

    def test_metrics_skew_angle_is_float(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """skew_angle が float であること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)
        assert isinstance(result.metrics["skew_angle"], float)

    def test_metrics_binarization_threshold_is_int(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """binarization_threshold が int であること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)
        assert isinstance(result.metrics["binarization_threshold"], int)

    def test_metrics_black_pixel_ratio_between_0_and_1(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """black_pixel_ratio が 0.0〜1.0 の範囲内であること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)
        ratio = result.metrics["black_pixel_ratio"]
        assert 0.0 <= float(ratio) <= 1.0


# ---------------------------------------------------------------------------
# preprocess() — 黒画素比率警告テスト
# ---------------------------------------------------------------------------


class TestPreprocessorBlackPixelWarnings:
    """黒画素比率の範囲外警告テスト群"""

    def test_no_warning_for_normal_black_pixel_ratio(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """黒画素比率が 5〜40% の場合は warnings が空であること"""
        from pipeline.ingest.preprocessor import preprocess

        # gray_png は黒い帯があり黒画素比率が適切な範囲に入るよう設計
        result = preprocess(gray_png, output_dir=output_dir)
        # warnings には黒画素比率関連のメッセージが入らないこと
        black_ratio_warnings = [
            w for w in result.warnings if "black pixel" in w.lower()
        ]
        assert len(black_ratio_warnings) == 0

    def test_warning_for_too_low_black_pixel_ratio(
        self, white_png: Path, output_dir: Path
    ) -> None:
        """黒画素比率が 5% 未満の場合は warnings にメッセージが追加されること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(white_png, output_dir=output_dir)
        black_ratio_warnings = [
            w for w in result.warnings if "black pixel" in w.lower()
        ]
        assert len(black_ratio_warnings) >= 1

    def test_warning_message_contains_ratio(
        self, white_png: Path, output_dir: Path
    ) -> None:
        """警告メッセージに比率の数値が含まれること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(white_png, output_dir=output_dir)
        black_ratio_warnings = [
            w for w in result.warnings if "black pixel" in w.lower()
        ]
        assert len(black_ratio_warnings) >= 1
        # 数値文字が含まれることを確認
        assert any(ch.isdigit() for ch in black_ratio_warnings[0])

    def test_warning_for_too_high_black_pixel_ratio(
        self, black_png: Path, output_dir: Path
    ) -> None:
        """黒画素比率が 40% 超の場合は warnings にメッセージが追加されること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(black_png, output_dir=output_dir)
        black_ratio_warnings = [
            w for w in result.warnings if "black pixel" in w.lower()
        ]
        assert len(black_ratio_warnings) >= 1


# ---------------------------------------------------------------------------
# preprocess() — デスキュー挙動テスト
# ---------------------------------------------------------------------------


class TestPreprocessorDeskew:
    """デスキュー（傾き補正）の動作テスト群"""

    def test_preprocess_uses_custom_deskew_threshold(self, gray_png: Path, output_dir: Path) -> None:
        from pipeline.ingest.preprocessor import preprocess

        mock_lines = np.array([[[0, 0, 100, 9]]], dtype=np.int32)

        with patch("pipeline.ingest.preprocessor.cv2.HoughLinesP", return_value=mock_lines):
            result = preprocess(gray_png, output_dir=output_dir, deskew_max_angle=3.0)

        assert any("Large skew angle detected" in warning for warning in result.warnings)

    def test_no_skew_warning_for_small_angle(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """HoughLinesP が None を返した場合（ライン未検出）は skew 警告なし"""
        from pipeline.ingest.preprocessor import preprocess

        with patch(
            "pipeline.ingest.preprocessor.cv2.HoughLinesP",
            return_value=None,
        ):
            result = preprocess(gray_png, output_dir=output_dir)

        skew_warnings = [w for w in result.warnings if "skew" in w.lower()]
        assert len(skew_warnings) == 0
        assert result.metrics["skew_angle"] == 0.0

    def test_large_skew_adds_warning(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """HoughLinesP が 20° の傾きを返した場合 warnings に skew メッセージが追加されること"""
        from pipeline.ingest.preprocessor import preprocess

        def mock_hough(
            image: object,
            rho: object,
            theta: object,
            threshold: object,
            **kwargs: object,
        ) -> object:
            angle_rad = math.radians(20.0)  # 20° > 10°
            x1, y1 = 10, 100
            x2 = x1 + int(180 * math.cos(angle_rad))
            y2 = y1 + int(180 * math.sin(angle_rad))
            return np.array([[[x1, y1, x2, y2]]])

        with patch(
            "pipeline.ingest.preprocessor.cv2.HoughLinesP",
            side_effect=mock_hough,
        ):
            result = preprocess(gray_png, output_dir=output_dir)

        skew_warnings = [w for w in result.warnings if "skew" in w.lower()]
        assert len(skew_warnings) >= 1

    def test_skew_angle_abs_less_than_90(
        self, gray_png: Path, output_dir: Path
    ) -> None:
        """metrics["skew_angle"] の絶対値が 90 未満であること"""
        from pipeline.ingest.preprocessor import preprocess

        result = preprocess(gray_png, output_dir=output_dir)
        assert abs(float(result.metrics["skew_angle"])) < 90.0
