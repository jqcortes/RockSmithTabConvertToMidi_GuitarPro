"""
pipeline/common.py — 全ドメイン共通型定義

全パイプラインドメインが依存する共有型・例外・ロガーを定義する。
このモジュール以外の pipeline/* モジュールを import してはならない。

Exports:
    StepResult   — ドメイン間インターフェース用 dataclass
    PipelineError — 全パイプライン例外の基底クラス
    IngestError  — Ingest ドメイン固有例外
    get_logger   — structlog バウンドロガー取得ユーティリティ
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias, Union, cast

import structlog

# ---------------------------------------------------------------------------
# ロガー設定
# ---------------------------------------------------------------------------

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)


def get_logger(name: str) -> structlog.BoundLogger:
    """指定した名前のバウンドロガーを返す。

    Args:
        name: ロガー識別子（通常は __name__ を渡す）

    Returns:
        structlog.BoundLogger インスタンス
    """
    return cast(structlog.BoundLogger, structlog.get_logger(name))


# ---------------------------------------------------------------------------
# データ型
# ---------------------------------------------------------------------------

OutputPath = Union[Path, list[Path]]
MetricValue: TypeAlias = float | int | str | bool | list[str] | dict[str, str]


@dataclass
class StepResult:
    """パイプライン各ステップの実行結果を表す。

    ドメイン間はこの型のみで通信し、直接 import での結合を避ける。

    Attributes:
        success:     ステップが正常完了した場合 True
        output_path: 出力ファイルパス（単一または複数ページ）
        metrics:     処理メトリクス（例: page_count, skew_angle）
        warnings:    非致命的な警告メッセージ一覧
    """

    success: bool
    output_path: OutputPath
    metrics: dict[str, MetricValue]
    warnings: list[str]

    @classmethod
    def ok(
        cls,
        output_path: OutputPath,
        *,
        metrics: dict[str, MetricValue] | None = None,
        warnings: list[str] | None = None,
    ) -> "StepResult":
        """success=True の StepResult を生成するファクトリメソッド。

        Args:
            output_path: 出力ファイルパス（Path または list[Path]）
            metrics:     処理メトリクス（省略時: 空 dict）
            warnings:    非致命的な警告一覧（省略時: 空 list）

        Returns:
            success=True の StepResult インスタンス
        """
        return cls(
            success=True,
            output_path=output_path,
            metrics=metrics if metrics is not None else {},
            warnings=warnings if warnings is not None else [],
        )


# ---------------------------------------------------------------------------
# 例外階層
# ---------------------------------------------------------------------------


class PipelineError(Exception):
    """全パイプラインエラーの基底クラス。

    すべてのドメイン固有例外はこのクラスを継承する。
    """


class IngestError(PipelineError):
    """Ingest ドメイン固有のエラー。

    ファイル不在・非対応フォーマット・低解像度など
    Ingest フェーズで発生する例外に使用する。
    """
