"""
pipeline/ingest/image_loader.py — PDF / 画像ファイル読み込みとキャッシュ管理

サポートフォーマット: PDF, PNG, TIFF, JPEG
出力: 300dpi PNG ファイルのリスト (cache_dir 以下)

Public API:
    load(input_path, cache_dir) -> StepResult
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import cast

from pdf2image import convert_from_path  # noqa: F401 — モックターゲットとして明示 import
from PIL import Image

from pipeline.common import IngestError, StepResult, get_logger

_log = get_logger(__name__)

# サポートするファイル拡張子（小文字）
_SUPPORTED_IMAGE_EXTS: frozenset[str] = frozenset({".png", ".tiff", ".tif", ".jpg", ".jpeg"})
_SUPPORTED_PDF_EXT: str = ".pdf"
_ALL_SUPPORTED: frozenset[str] = _SUPPORTED_IMAGE_EXTS | {_SUPPORTED_PDF_EXT}


def load(
    input_path: Path,
    cache_dir: Path = Path(".cache/ingest"),
    *,
    target_dpi: int = 300,
) -> StepResult:
    """入力ファイルを 300dpi PNG に変換してキャッシュディレクトリへ保存する。

    Args:
        input_path: 読み込む PDF / PNG / TIFF / JPEG ファイルのパス
        cache_dir:  変換後 PNG の保存先ディレクトリ（存在しない場合は自動作成）

    Returns:
        StepResult:
            output_path — list[Path]（変換済み PNG のリスト）
            metrics     — {"page_count": int, "cached": bool}

    Raises:
        IngestError: ファイルが存在しない、または非対応拡張子の場合
    """
    # --- バリデーション ---
    if not input_path.exists():
        raise IngestError(f"File not found: {input_path}")

    ext = input_path.suffix.lower()
    if ext not in _ALL_SUPPORTED:
        raise IngestError(
            f"Unsupported format: {ext}. "
            f"Supported: pdf, png, tiff, tif, jpg, jpeg"
        )

    # --- キャッシュディレクトリ作成 ---
    cache_dir.mkdir(parents=True, exist_ok=True)

    if ext == _SUPPORTED_PDF_EXT:
        return _load_pdf(input_path, cache_dir, target_dpi=target_dpi)
    else:
        return _load_image(input_path, cache_dir)


def _load_pdf(pdf_path: Path, cache_dir: Path, *, target_dpi: int) -> StepResult:
    """PDF ファイルを 300dpi PNG ページ群に変換してキャッシュへ保存する。"""
    stem = pdf_path.stem

    # キャッシュヒット判定: {stem}_p001.png が存在すればヒット
    first_page_cache = cache_dir / f"{stem}_p001.png"
    if first_page_cache.exists():
        # キャッシュ済みページをすべて収集
        cached_pages = sorted(cache_dir.glob(f"{stem}_p*.png"))
        if _cached_pages_meet_target_dpi(cached_pages, target_dpi):
            _log.info(
                "pdf_cache_hit",
                path=str(pdf_path),
                page_count=len(cached_pages),
            )
            return StepResult.ok(
                cached_pages,
                metrics={"page_count": len(cached_pages), "cached": True},
            )

        _log.info(
            "pdf_cache_invalid_dpi",
            path=str(pdf_path),
            page_count=len(cached_pages),
            required_dpi=target_dpi,
        )
        for cached_page in cached_pages:
            cached_page.unlink(missing_ok=True)

    # キャッシュミス → 変換実行
    _log.info("pdf_converting", path=str(pdf_path), dpi=target_dpi)
    pages = convert_from_path(str(pdf_path), dpi=target_dpi)

    output_paths: list[Path] = []
    for i, page in enumerate(pages, start=1):
        out_path = cache_dir / f"{stem}_p{i:03d}.png"
        page.save(str(out_path), "PNG", dpi=(target_dpi, target_dpi))
        output_paths.append(out_path)

    _log.info("pdf_converted", path=str(pdf_path), page_count=len(output_paths))
    return StepResult.ok(
        output_paths,
        metrics={"page_count": len(output_paths), "cached": False},
    )


def _load_image(image_path: Path, cache_dir: Path) -> StepResult:
    """PNG / TIFF / JPEG ファイルをキャッシュディレクトリへコピーする。"""
    dest = cache_dir / image_path.name

    if dest.exists():
        _log.info("image_cache_hit", path=str(image_path))
        return StepResult.ok(
            [dest],
            metrics={"page_count": 1, "cached": True},
        )

    shutil.copy2(str(image_path), str(dest))
    _log.info("image_copied", path=str(image_path), dest=str(dest))
    return StepResult.ok(
        [dest],
        metrics={"page_count": 1, "cached": False},
    )


def _cached_pages_meet_target_dpi(cached_pages: list[Path], target_dpi: int) -> bool:
    if not cached_pages:
        return False

    for page_path in cached_pages:
        dpi = _read_image_dpi(page_path)
        if dpi is None or dpi < float(target_dpi):
            return False
    return True


def _read_image_dpi(image_path: Path) -> float | None:
    try:
        with Image.open(image_path) as img:
            raw_dpi = img.info.get("dpi")
    except OSError:
        return None

    if not isinstance(raw_dpi, tuple) or len(raw_dpi) != 2:
        return None

    x_dpi, y_dpi = raw_dpi
    if not isinstance(x_dpi, (int, float)) or not isinstance(y_dpi, (int, float)):
        return None

    return float(round(min(x_dpi, y_dpi)))
