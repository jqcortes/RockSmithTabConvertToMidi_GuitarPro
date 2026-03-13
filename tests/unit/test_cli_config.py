"""tests for CLI pipeline config loading."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_load_pipeline_config_resolves_relative_properties_path(tmp_path: Path) -> None:
    from pipeline.cli_config import load_pipeline_config

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "pipeline.yaml"
    config_path.write_text(
        "audiveris:\n"
        "  properties_path: audiveris.properties\n"
        "quality:\n"
        "  pass_threshold: 0.85\n"
        "  warn_threshold: 0.55\n",
        encoding="utf-8",
    )

    loaded = load_pipeline_config(config_path)

    assert loaded.properties_path == (config_dir / "audiveris.properties").resolve()
    assert loaded.quality.pass_threshold == 0.85
    assert loaded.quality.warn_threshold == 0.55


def test_load_pipeline_config_uses_repository_default_properties_path() -> None:
    from pipeline.cli_config import load_pipeline_config

    config_path = Path("config/pipeline.yaml")

    loaded = load_pipeline_config(config_path)

    assert loaded.properties_path == Path("config/audiveris.properties").resolve()


def test_load_pipeline_config_raises_for_missing_file(tmp_path: Path) -> None:
    from pipeline.cli_config import load_pipeline_config
    from pipeline.common import PipelineError

    with pytest.raises(PipelineError, match="Pipeline config not found"):
        load_pipeline_config(tmp_path / "missing.yaml")


def test_load_pipeline_config_rejects_invalid_thresholds(tmp_path: Path) -> None:
    from pipeline.cli_config import load_pipeline_config
    from pipeline.common import PipelineError

    config_path = tmp_path / "pipeline.yaml"
    config_path.write_text(
        "audiveris:\n"
        "  properties_path: config/audiveris.properties\n"
        "quality:\n"
        "  pass_threshold: 0.4\n"
        "  warn_threshold: 0.6\n",
        encoding="utf-8",
    )

    with pytest.raises(PipelineError, match="warn_threshold"):
        load_pipeline_config(config_path)