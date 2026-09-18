"""config/instruments.yaml（MuScriptor 実測楽器名）のロードと検証。

T0-2 の DoD: 実測が完了するまで `verified: false` のまま。未実測の間も
処理は継続できるが、警告を出す。
"""
from __future__ import annotations

from pathlib import Path

import yaml

INSTRUMENTS_PATH = Path(__file__).resolve().parents[2] / "config" / "instruments.yaml"


class Instruments:
    def __init__(self, verified: bool, guitar: list[str], bass: list[str]) -> None:
        self.verified = verified
        self.guitar = guitar
        self.bass = bass

    @classmethod
    def load(cls, path: Path | None = None) -> Instruments:
        raw = yaml.safe_load((path or INSTRUMENTS_PATH).read_text(encoding="utf-8")) or {}
        return cls(
            verified=bool(raw.get("verified", False)),
            guitar=list(raw.get("guitar", [])),
            bass=list(raw.get("bass", [])),
        )

    def validate(self, requested: list[str], kind: str) -> None:
        known = self.guitar if kind == "guitar" else self.bass
        unknown = [name for name in requested if name not in known]
        if unknown:
            raise ValueError(
                f"未知の楽器名です: {unknown}. config/instruments.yaml の {kind} 一覧を確認してください "
                f"(scripts/probe_muscriptor.py で実測すること)。"
            )
