"""Tests for declarative scenario file loading."""

import json
from pathlib import Path

from scenario_controller import ScenarioController


def test_list_scenario_files(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"name": "A"}))
    (tmp_path / "b.json").write_text(json.dumps({"name": "B"}))
    (tmp_path / "readme.txt").write_text("ignore me")

    files = ScenarioController.list_scenario_files(tmp_path)
    names = [f.name for f in files]
    assert "a.json" in names
    assert "b.json" in names
    assert "readme.txt" not in names


def test_list_scenario_files_missing_dir():
    assert ScenarioController.list_scenario_files("/nonexistent") == []
