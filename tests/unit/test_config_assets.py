"""Repository config asset validation tests."""

from __future__ import annotations

import configparser
from pathlib import Path

import yaml


def test_audiveris_properties_contains_required_defaults() -> None:
    config_path = Path("config/audiveris.properties")
    assert config_path.exists()

    parser = configparser.ConfigParser()
    parser.optionxform = str  # type: ignore[assignment]
    parser.read(config_path, encoding="utf-8")

    defaults = parser.defaults()
    # 値は引用符付き文字列の場合があるため strip して大文字小文字を無視して確認
    jar_value = defaults["audiveris.jar"].strip().strip('"').strip("'")
    assert jar_value.lower().endswith("audiveris.jar")
    assert defaults["audiveris.timeout"] == "300"
    # 旧 LineClusterAdapter キーは削除済み; ProcessingSwitches の正式キーで検証する
    assert defaults[
        "audiveris.option.org.audiveris.omr.sheet.ProcessingSwitches.sixStringTablatures"
    ] == "true"
    assert defaults[
        "audiveris.option.org.audiveris.omr.sig.inter.AbstractInter.minGrade"
    ] == "0.35"


def test_pipeline_yaml_contains_documented_sections() -> None:
    config_path = Path("config/pipeline.yaml")
    assert config_path.exists()

    content = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert isinstance(content, dict)

    assert set(content) == {"audiveris", "preprocessing", "quality", "midi"}
    assert content["audiveris"]["properties_path"] == "audiveris.properties"
    assert content["audiveris"]["timeout_seconds"] == 300
    assert content["preprocessing"]["target_dpi"] == 300
    assert content["quality"]["pass_threshold"] == 0.80
    assert content["quality"]["warn_threshold"] == 0.60
    assert content["quality"]["pass_threshold"] > content["quality"]["warn_threshold"]
    assert content["midi"]["default_tempo"] == 120


def test_instrument_map_yaml_contains_tunings_and_part_mappings() -> None:
    config_path = Path("config/instrument_map.yaml")
    content = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert isinstance(content, dict)
    tunings = content["tunings"]
    assert tunings["standard"] == [40, 45, 50, 55, 59, 64]
    assert tunings["drop_d"] == [38, 45, 50, 55, 59, 64]

    parts = content["parts"]
    assert isinstance(parts, list)
    assert len(parts) >= 4
    guitar = next(part for part in parts if part["role"] == "guitar")
    drums = next(part for part in parts if part["role"] == "drums")

    assert guitar["midi_channel"] == 1
    assert guitar["midi_program"] == 29
    assert guitar["transpose"] == -12
    assert drums["midi_channel"] == 10
    assert drums["midi_program"] == 0