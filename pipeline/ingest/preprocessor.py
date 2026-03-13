"""
pipeline/ingest/preprocessor.py — 画像前処理パイプライン

入力 PNG をAudiveris が高精度で読み取れる品質に変換する。
処理ステップ（順番固定）:
  1. グレースケール変換
  2. デスキュー (HoughLinesP + getRotationMatrix2D)
  3. Otsu 二値化
  4. CLAHE コントラスト正規化
  5. 余白トリミング (boundingRect)

Public API:
    preprocess(image_path, output_dir) -> StepResult
"""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from pipeline.common import MetricValue, StepResult, get_logger

_log = get_logger(__name__)

# デスキュー：この角度（度）を超えたら補正せず警告のみ
_MAX_DESKEW_ANGLE: float = 10.0

# 黒画素比率の正常範囲
_BLACK_RATIO_MIN: float = 0.05
_BLACK_RATIO_MAX: float = 0.40


def preprocess(
    image_path: Path,
    output_dir: Path = Path(".cache/preprocess"),
    *,
    deskew_max_angle: float = _MAX_DESKEW_ANGLE,
    clahe_clip_limit: float = 2.0,
) -> StepResult:
    """画像前処理パイプラインを実行し、前処理済み PNG を返す。

    Args:
        image_path: 入力 PNG ファイルパス
        output_dir: 前処理済み PNG の保存先（存在しない場合は自動作成）

    Returns:
        StepResult:
            output_path — Path (前処理済み PNG 単一ファイル)
            metrics     — {skew_angle: float, binarization_threshold: int, black_pixel_ratio: float}
            warnings    — 非致命的な品質警告のリスト
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    source_dpi = _read_source_dpi(image_path)

    img = cv2.imread(str(image_path))
    gray: np.ndarray
    if img is None:
        # 読み込み失敗時はグレースケール再試行（拡張子が非標準の場合）
        decoded = cv2.imdecode(
            np.frombuffer(image_path.read_bytes(), dtype=np.uint8),
            cv2.IMREAD_GRAYSCALE,
        )
        if decoded is None:
            from pipeline.common import IngestError
            raise IngestError(f"Failed to decode image: {image_path}")
        gray = decoded
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    warnings: list[str] = []
    metrics: dict[str, MetricValue] = {}

    # ---- Step 1.5: ノイズ除去（スキュー検出精度とOMR品質向上） ----
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # ---- Step 2: デスキュー ----
    gray, skew_angle = _deskew(gray, warnings, deskew_max_angle=deskew_max_angle)
    metrics["skew_angle"] = skew_angle

    # ---- Step 3: CLAHE（グレースケール段階でコントラスト正規化） ----
    clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # ---- Step 4: Otsu 二値化 ----
    thresh_val, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    metrics["binarization_threshold"] = int(thresh_val)

    # ---- Step 5: 余白トリミング ----
    img = _trim_margins(binary)

    # ---- 後処理チェック: 黒画素比率 ----
    # Otsu 二値化後は 0 / 255 の二値なので == 0 で黒画素を計測する
    black_ratio = float(np.sum(img == 0)) / float(img.size)
    metrics["black_pixel_ratio"] = black_ratio

    if black_ratio < _BLACK_RATIO_MIN or black_ratio > _BLACK_RATIO_MAX:
        warnings.append(
            f"Unusual black pixel ratio: {black_ratio:.1%} "
            f"(expected {_BLACK_RATIO_MIN:.0%}–{_BLACK_RATIO_MAX:.0%})"
        )

    # ---- 出力保存 ----
    out_path = output_dir / image_path.name
    Image.fromarray(img).save(out_path, dpi=source_dpi)

    _log.info(
        "preprocess_done",
        input=str(image_path),
        skew_angle=skew_angle,
        black_pixel_ratio=f"{black_ratio:.1%}",
        warnings=len(warnings),
    )
    return StepResult.ok(out_path, metrics=metrics, warnings=warnings)


def _deskew(
    img: np.ndarray,
    warnings: list[str],
    *,
    deskew_max_angle: float,
) -> tuple[np.ndarray, float]:
    """HoughLinesP でスタッフラインの傾きを検出し、補正する。

    ±10° を超える傾きは補正しない（警告のみ追加）。

    Returns:
        (補正済み画像, 検出した傾き角度[度]) のタプル
    """
    lines = cv2.HoughLinesP(
        img,
        rho=1,
        theta=math.pi / 180,
        threshold=100,
        minLineLength=img.shape[1] // 4,
        maxLineGap=20,
    )

    if lines is None:
        return img, 0.0

    # 検出ライン全体から近水平線（|angle| < 30°）のみ抽出してスキュー計算。
    # -45° 付近の斜線（タイ・スラー・コード記号等）がバイアスするのを防ぐ。
    all_angles: list[float] = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle_deg = math.degrees(math.atan2(float(y2 - y1), float(x2 - x1)))
        all_angles.append(angle_deg)

    horizontal_angles = [a for a in all_angles if abs(a) < 30.0]
    if not horizontal_angles:
        # 水平線が検出されなかった場合、全ラインの中央値をフォールバックとして使用
        horizontal_angles = all_angles

    skew_angle = float(np.median(horizontal_angles))

    if abs(skew_angle) > deskew_max_angle:
        warnings.append(
            f"Large skew angle detected: {skew_angle:.1f}° "
            f"(threshold ±{deskew_max_angle}°). Skipping correction."
        )
        return img, skew_angle

    # 補正実行
    h, w = img.shape[:2]
    center = (w / 2.0, h / 2.0)
    rot_mat = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
    corrected: np.ndarray = cv2.warpAffine(
        img,
        rot_mat,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return corrected, skew_angle


def _trim_margins(img: np.ndarray) -> np.ndarray:
    """楽譜領域の外接矩形を検出して余白をトリミングする。

    輪郭が検出できない場合は入力をそのまま返す。
    """
    # 黒画素の輪郭を検出（二値化済み想定: 黒=0, 白=255）
    # 反転して黒領域を白として findContours に渡す
    inverted = cv2.bitwise_not(img)
    contours, _ = cv2.findContours(
        inverted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return img

    # 全輪郭を包む外接矩形
    all_pts = np.concatenate(contours)
    x, y, w, h = cv2.boundingRect(all_pts)

    # 小さすぎる場合はトリミングしない（ノイズ除去）
    if w < 10 or h < 10:
        return img

    return img[y : y + h, x : x + w]


def _read_source_dpi(image_path: Path) -> tuple[float, float]:
    with Image.open(image_path) as source_image:
        raw_dpi = source_image.info.get("dpi", (72.0, 72.0))

    if not isinstance(raw_dpi, tuple) or len(raw_dpi) != 2:
        return (72.0, 72.0)

    x_dpi, y_dpi = raw_dpi
    if not isinstance(x_dpi, (int, float)) or not isinstance(y_dpi, (int, float)):
        return (72.0, 72.0)

    return (float(x_dpi), float(y_dpi))
