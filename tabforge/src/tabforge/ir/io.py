"""IR の load/save。schema フィールドのバージョン検証を必須にする。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class SchemaVersionError(ValueError):
    """保存されている schema と読み込もうとしたモデルの schema が不一致。"""


def save(model: BaseModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = model.model_dump(by_alias=True, mode="json")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load(model_cls: type[T], path: Path) -> T:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "schema" not in raw:
        raise SchemaVersionError(f"{path}: 'schema' フィールドが存在しない")
    expected = model_cls.model_fields["schema_"].default
    if raw["schema"] != expected:
        raise SchemaVersionError(
            f"{path}: schema mismatch. expected={expected!r} actual={raw['schema']!r}"
        )
    try:
        return model_cls.model_validate(raw)
    except ValidationError as exc:
        raise SchemaVersionError(f"{path}: バリデーション失敗: {exc}") from exc
