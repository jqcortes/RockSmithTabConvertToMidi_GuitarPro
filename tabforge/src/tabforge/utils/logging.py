"""構造化ログ（JSON Lines）。ステージ名・所要時間・警告を記録する。"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class StageLogger:
    stream: Any = sys.stderr

    def _emit(self, level: str, stage: str, message: str, **fields: Any) -> None:
        record = {
            "ts": time.time(),
            "level": level,
            "stage": stage,
            "message": message,
            **fields,
        }
        print(json.dumps(record, ensure_ascii=False), file=self.stream)

    def info(self, stage: str, message: str, **fields: Any) -> None:
        self._emit("info", stage, message, **fields)

    def warning(self, stage: str, message: str, **fields: Any) -> None:
        self._emit("warning", stage, message, **fields)

    def error(self, stage: str, message: str, **fields: Any) -> None:
        self._emit("error", stage, message, **fields)
