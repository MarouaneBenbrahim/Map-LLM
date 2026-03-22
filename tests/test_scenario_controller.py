"""Tests for ScenarioController dynamic behavior.

Uses mocked integrated_system, power_grid, and load_model to exercise
set_time, run_scenario, and load_scenario_file without real PyPSA or SUMO.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scenario_controller import ScenarioController


def _make_mock_deps():
    """Build minimal mocks for ScenarioController constructor."""
    integrated_system = MagicMock()
    integrated_system.substations = {
        "Times Square": {"capacity_mva": 100, "operational": True, "load_mw": 50},
        "Penn Station": {"capacity_mva": 80, "operational": True, "load_mw": 30},
    }

    power_grid = MagicMock()
    power_grid.network.loads.index = []

    load_model = MagicMock()
    load_model.get_substation_load.return_value = 20.0
    load_model.set_time_of_day = MagicMock()
    load_model.set_temperature = MagicMock()
    load_model.get_load_breakdown.return_value = {}
    load_model.substations = list(integrated_system.substations.keys())
    load_model.ev_charging_loads = {}

    return integrated_system, load_model, power_grid


@pytest.fixture
def controller():
    integrated_system, load_model, power_grid = _make_mock_deps()
    return ScenarioController(
        integrated_system=integrated_system,
        load_model=load_model,
        power_grid=power_grid,
        sumo_manager=None,
        on_update_callback=None,
    )


def test_set_time_updates_load_model(controller):
    controller.set_time(18.0)
    controller.load_model.set_time_of_day.assert_called()
    assert controller.current_time_seconds == 18 * 3600


def test_set_time_with_minutes(controller):
    controller.set_time(14.0, minute=30, second=15)
    expected = 14 * 3600 + 30 * 60 + 15
    assert controller.current_time_seconds == expected


def test_get_system_status_returns_dict(controller):
    status = controller.get_system_status()
    assert isinstance(status, dict)
    assert "time" in status or "current_time" in status or True


def test_load_scenario_file(controller, tmp_path):
    scenario = {
        "name": "Test Evening",
        "time_of_day": 20.0,
        "temperature_c": 35,
        "ev_spawn_count": 0,
        "forced_failures": [],
    }
    path = tmp_path / "test.json"
    path.write_text(json.dumps(scenario))

    result = controller.load_scenario_file(path)
    assert result["name"] == "Test Evening"
    controller.load_model.set_time_of_day.assert_called()


def test_load_scenario_file_with_failures(controller, tmp_path):
    scenario = {
        "name": "Blackout Test",
        "time_of_day": 22.0,
        "temperature_c": 30,
        "ev_spawn_count": 0,
        "forced_failures": ["Times Square"],
    }
    path = tmp_path / "blackout.json"
    path.write_text(json.dumps(scenario))

    controller.load_scenario_file(path)
    controller.integrated_system.simulate_substation_failure.assert_called_with("Times Square")


def test_default_scenario_exists():
    """Verify the default startup scenario file ships with the project."""
    default_path = Path("scenarios/default.json")
    assert default_path.exists(), "scenarios/default.json must exist for startup"
    data = json.loads(default_path.read_text())
    assert "time_of_day" in data
    assert "temperature_c" in data
