"""
Unit tests for pipeline/ingest/image_loader.py — TDD: RED phase

Task 2 scope:
- load(input_path, cache_dir) -> StepResult
- PDF → 300dpi PNG 変換（pdf2image モック化）
- PNG/TIFF/JPEG → cache_dir コピー
- キャッシュヒット時はスキップ
- 非対応拡張子・ファイル不在 → IngestError
- StepResult.metrics = {"page_count": int, "cached": bool}
- StepResult.output_path = list[Path]
"""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_cache(tmp_path: Path) -> Path:
    """一時キャッシュディレクトリを返す。"""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


@pytest.fixture()
def sample_png(tmp_path: Path) -> Path:
    """1×1 ピクセルの最小 PNG ファイルを作成して返す。"""
    from PIL import Image

    img_path = tmp_path / "sample.png"
    img = Image.new("RGB", (1, 1))
    img.save(img_path)
    return img_path


@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    """空ファイルを PDF 拡張子で作成して返す（内容は pdf2image モックで処理）。"""
    pdf_path = tmp_path / "score.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    return pdf_path


# ---------------------------------------------------------------------------
# load() — PDF 変換テスト
# ---------------------------------------------------------------------------


class TestImageLoaderPdf:
    """PDF 入力のテスト群"""

    def test_load_pdf_returns_stepresult(
        self, sample_pdf: Path, tmp_cache: Path, tmp_path: Path
    ) -> None:
        """PDF を渡すと StepResult が返ること"""
        from pipeline.ingest.image_loader import load

        fake_page = MagicMock()
        fake_page.save = MagicMock()

        with patch("pipeline.ingest.image_loader.convert_from_path") as mock_convert:
            mock_convert.return_value = [fake_page]
            result = load(sample_pdf, cache_dir=tmp_cache)

        from pipeline.common import StepResult
        assert isinstance(result, StepResult)

    def test_load_pdf_calls_convert_with_300dpi(
        self, sample_pdf: Path, tmp_cache: Path
    ) -> None:
        """pdf2image.convert_from_path が dpi=300 で呼び出されること"""
        from pipeline.ingest.image_loader import load

        fake_page = MagicMock()

        with patch("pipeline.ingest.image_loader.convert_from_path") as mock_convert:
            mock_convert.return_value = [fake_page]
            load(sample_pdf, cache_dir=tmp_cache)

        mock_convert.assert_called_once()
        _, kwargs = mock_convert.call_args
        assert kwargs.get("dpi") == 300 or mock_convert.call_args.args[1:] == (300,) or kwargs.get("dpi", mock_convert.call_args.args[1] if len(mock_convert.call_args.args) > 1 else None) == 300

    def test_load_pdf_saves_pages_with_correct_naming(
        self, sample_pdf: Path, tmp_cache: Path
    ) -> None:
        """変換されたページが {stem}_p001.png, {stem}_p002.png 形式で保存されること"""
        from pipeline.ingest.image_loader import load

        fake_page1 = MagicMock()
        fake_page2 = MagicMock()

        with patch("pipeline.ingest.image_loader.convert_from_path") as mock_convert:
            mock_convert.return_value = [fake_page1, fake_page2]
            result = load(sample_pdf, cache_dir=tmp_cache)

        paths = result.output_path
        assert isinstance(paths, list)
        assert len(paths) == 2
        assert paths[0].name == "score_p001.png"
        assert paths[1].name == "score_p002.png"

    def test_load_pdf_metrics_page_count(
        self, sample_pdf: Path, tmp_cache: Path
    ) -> None:
        """metrics["page_count"] がページ数と一致すること"""
        from pipeline.ingest.image_loader import load

        fake_pages = [MagicMock(), MagicMock(), MagicMock()]

        with patch("pipeline.ingest.image_loader.convert_from_path") as mock_convert:
            mock_convert.return_value = fake_pages
            result = load(sample_pdf, cache_dir=tmp_cache)

        assert result.metrics["page_count"] == 3

    def test_load_pdf_metrics_cached_false_on_first_load(
        self, sample_pdf: Path, tmp_cache: Path
    ) -> None:
        """初回変換時は metrics["cached"] が False であること"""
        from pipeline.ingest.image_loader import load

        with patch("pipeline.ingest.image_loader.convert_from_path") as mock_convert:
            mock_convert.return_value = [MagicMock()]
            result = load(sample_pdf, cache_dir=tmp_cache)

        assert result.metrics["cached"] is False

    def test_load_pdf_cache_hit_skips_conversion(
        self, sample_pdf: Path, tmp_cache: Path
    ) -> None:
        """キャッシュファイルが存在する場合は pdf2image を呼ばず cached=True を返すこと"""
        from pipeline.ingest.image_loader import load
        from PIL import Image

        # キャッシュファイルを事前配置
        cached_file = tmp_cache / "score_p001.png"
        Image.new("L", (1, 1), 255).save(cached_file, dpi=(300, 300))

        with patch("pipeline.ingest.image_loader.convert_from_path") as mock_convert:
            result = load(sample_pdf, cache_dir=tmp_cache)

        mock_convert.assert_not_called()
        assert result.metrics["cached"] is True
        assert Path(result.output_path[0]) == cached_file  # type: ignore[index]

    def test_load_pdf_cache_hit_with_missing_dpi_rebuilds_cache(
        self, sample_pdf: Path, tmp_cache: Path
    ) -> None:
        """キャッシュPNGにDPIが無い場合は再変換して cached=False を返すこと"""
        from pipeline.ingest.image_loader import load
        from PIL import Image

        cached_file = tmp_cache / "score_p001.png"
        Image.new("L", (1, 1), 255).save(cached_file)  # dpi なし

        fake_page = MagicMock()
        with patch("pipeline.ingest.image_loader.convert_from_path") as mock_convert:
            mock_convert.return_value = [fake_page]
            result = load(sample_pdf, cache_dir=tmp_cache)

        mock_convert.assert_called_once()
        assert result.metrics["cached"] is False

    def test_load_pdf_saves_with_target_dpi_metadata(
        self, sample_pdf: Path, tmp_cache: Path
    ) -> None:
        """PDF変換後のPNG保存時に target_dpi がメタデータとして設定されること"""
        from pipeline.ingest.image_loader import load

        fake_page = MagicMock()
        with patch("pipeline.ingest.image_loader.convert_from_path") as mock_convert:
            mock_convert.return_value = [fake_page]
            load(sample_pdf, cache_dir=tmp_cache, target_dpi=240)

        fake_page.save.assert_called_once()
        _, kwargs = fake_page.save.call_args
        assert kwargs.get("dpi") == (240, 240)

    def test_load_pdf_success_is_true(
        self, sample_pdf: Path, tmp_cache: Path
    ) -> None:
        """正常完了時に success=True であること"""
        from pipeline.ingest.image_loader import load

        with patch("pipeline.ingest.image_loader.convert_from_path") as mock_convert:
            mock_convert.return_value = [MagicMock()]
            result = load(sample_pdf, cache_dir=tmp_cache)

        assert result.success is True

    def test_load_pdf_uses_custom_target_dpi(
        self, sample_pdf: Path, tmp_cache: Path
    ) -> None:
        """カスタム target_dpi を指定すると pdf2image にその値が渡ること"""
        from pipeline.ingest.image_loader import load

        with patch("pipeline.ingest.image_loader.convert_from_path") as mock_convert:
            mock_convert.return_value = [MagicMock()]
            load(sample_pdf, cache_dir=tmp_cache, target_dpi=240)

        _, kwargs = mock_convert.call_args
        assert kwargs.get("dpi") == 240 or mock_convert.call_args.args[1:] == (240,)


# ---------------------------------------------------------------------------
# load() — PNG/TIFF/JPEG コピーテスト
# ---------------------------------------------------------------------------


class TestImageLoaderImageFiles:
    """PNG / TIFF / JPEG 入力のテスト群"""

    def test_load_png_copies_to_cache(
        self, sample_png: Path, tmp_cache: Path
    ) -> None:
        """PNG を渡すとキャッシュディレクトリにコピーされること"""
        from pipeline.ingest.image_loader import load

        result = load(sample_png, cache_dir=tmp_cache)

        assert isinstance(result.output_path, list)
        assert len(result.output_path) == 1
        assert result.output_path[0].exists()
        assert result.output_path[0].name == "sample.png"

    def test_load_png_metrics(self, sample_png: Path, tmp_cache: Path) -> None:
        """PNG ロード時の metrics が正しいこと"""
        from pipeline.ingest.image_loader import load

        result = load(sample_png, cache_dir=tmp_cache)

        assert result.metrics["page_count"] == 1
        assert result.metrics["cached"] is False

    def test_load_png_cache_hit_skips_copy(
        self, sample_png: Path, tmp_cache: Path
    ) -> None:
        """キャッシュ済み PNG はコピーをスキップして cached=True を返すこと"""
        from pipeline.ingest.image_loader import load

        # 事前にキャッシュへ配置
        cached = tmp_cache / "sample.png"
        shutil.copy(sample_png, cached)

        result = load(sample_png, cache_dir=tmp_cache)

        assert result.metrics["cached"] is True

    def test_load_tiff_supported(self, tmp_path: Path, tmp_cache: Path) -> None:
        """TIFF ファイルがサポートされること"""
        from PIL import Image
        from pipeline.ingest.image_loader import load

        tiff_path = tmp_path / "score.tiff"
        Image.new("RGB", (1, 1)).save(tiff_path)

        result = load(tiff_path, cache_dir=tmp_cache)

        assert result.success is True
        assert len(result.output_path) == 1  # type: ignore[arg-type]

    def test_load_jpeg_supported(self, tmp_path: Path, tmp_cache: Path) -> None:
        """JPEG ファイルがサポートされること"""
        from PIL import Image
        from pipeline.ingest.image_loader import load

        jpg_path = tmp_path / "score.jpg"
        Image.new("RGB", (1, 1)).save(jpg_path)

        result = load(jpg_path, cache_dir=tmp_cache)

        assert result.success is True

    def test_load_creates_cache_dir_if_not_exists(
        self, sample_png: Path, tmp_path: Path
    ) -> None:
        """cache_dir が存在しない場合は自動作成すること"""
        from pipeline.ingest.image_loader import load

        new_cache = tmp_path / "new" / "cache"
        assert not new_cache.exists()

        load(sample_png, cache_dir=new_cache)

        assert new_cache.exists()


# ---------------------------------------------------------------------------
# load() — エラーケーステスト
# ---------------------------------------------------------------------------


class TestImageLoaderErrors:
    """エラーハンドリングのテスト群"""

    def test_load_file_not_found_raises_ingest_error(
        self, tmp_cache: Path
    ) -> None:
        """存在しないファイルパスで IngestError が raise されること"""
        from pipeline.common import IngestError
        from pipeline.ingest.image_loader import load

        missing = Path("/nonexistent/path/score.pdf")

        with pytest.raises(IngestError, match="File not found"):
            load(missing, cache_dir=tmp_cache)

    def test_load_unsupported_format_raises_ingest_error(
        self, tmp_path: Path, tmp_cache: Path
    ) -> None:
        """非対応拡張子で IngestError が raise されること"""
        from pipeline.common import IngestError
        from pipeline.ingest.image_loader import load

        docx = tmp_path / "score.docx"
        docx.write_bytes(b"fake docx")

        with pytest.raises(IngestError, match="Unsupported format"):
            load(docx, cache_dir=tmp_cache)

    def test_load_unsupported_format_error_message_contains_ext(
        self, tmp_path: Path, tmp_cache: Path
    ) -> None:
        """エラーメッセージに拡張子が含まれること"""
        from pipeline.common import IngestError
        from pipeline.ingest.image_loader import load

        bad_file = tmp_path / "score.xyz"
        bad_file.write_bytes(b"garbage")

        with pytest.raises(IngestError, match=r"\.xyz"):
            load(bad_file, cache_dir=tmp_cache)

    def test_load_output_path_is_always_list(
        self, sample_png: Path, tmp_cache: Path
    ) -> None:
        """output_path は常に list[Path] であること（単一ファイルも list）"""
        from pipeline.ingest.image_loader import load

        result = load(sample_png, cache_dir=tmp_cache)

        assert isinstance(result.output_path, list)
