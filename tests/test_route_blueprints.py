"""Tests for the extracted Flask Blueprint modules.

Each blueprint is initialized with lightweight mocks and exercised through
Flask's test client to verify route registration and basic JSON responses.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from app.core_routes import bp as core_bp, init_core_routes
from app.sumo_routes import bp as sumo_bp, init_sumo_routes
from app.grid_routes import bp as grid_bp, init_grid_routes
from app.v2g_routes import bp as v2g_bp, init_v2g_routes
from app.ai_routes import bp as ai_bp, init_ai_routes


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def _make_power_grid():
    pg = MagicMock()
    pg.network.buses.index = ["TestBus_13.8kV"]
    pg.network.loads.index = []
    pg.network.generators.index = []
    pg.get_system_status.return_value = {"substations": {}}
    # Prevent the debug_pypsa route from entering the loads_t branch
    pg.network.loads_t = MagicMock(spec=[])
    return pg


def _make_integrated_system():
    sis = MagicMock()
    sis.substations = {}
    sis.ev_stations = {}
    sis.traffic_lights = {}
    sis.distribution_transformers = {}
    sis.primary_cables = []
    sis.secondary_cables = []
    sis.get_network_state.return_value = {
        "substations": [],
        "ev_stations": [],
        "statistics": {},
    }
    return sis


def _make_sumo_manager():
    sm = MagicMock()
    sm.running = False
    sm.vehicles = {}
    sm.stats = {"total_vehicles": 0}
    sm.ev_stations_sumo = {}
    sm.get_statistics.return_value = {
        "total_vehicles": 0,
        "ev_vehicles": 0,
        "vehicles_charging": 0,
        "avg_speed_mps": 0,
        "total_energy_consumed_kwh": 0,
    }
    return sm


def _make_v2g_manager():
    vm = MagicMock()
    vm.active_sessions = {}
    vm.get_v2g_dashboard_data.return_value = {
        "enabled_substations": [],
        "active_sessions": [],
        "active_vehicles": [],
    }
    return vm


def _make_system_state():
    return {
        "sumo_running": False,
        "simulation_speed": 1.0,
        "scenario": SimpleNamespace(value="MIDDAY"),
        "running": True,
        "current_time": 0,
    }


# ---------------------------------------------------------------------------
# Core routes
# ---------------------------------------------------------------------------

class TestCoreRoutes:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        init_core_routes(
            power_grid=_make_power_grid(),
            integrated_system=_make_integrated_system(),
            sumo_manager=_make_sumo_manager(),
            v2g_manager=_make_v2g_manager(),
            system_state=_make_system_state(),
        )
        self.app.register_blueprint(core_bp)
        self.client = self.app.test_client()

    def test_config(self):
        resp = self.client.get("/api/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "mapbox_token" in data

    def test_debug_buses(self):
        resp = self.client.get("/api/debug/buses")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "pypsa_buses_13kv" in data

    def test_debug_pypsa(self):
        resp = self.client.get("/api/debug/pypsa")
        assert resp.status_code == 200

    def test_debug_ev_stations(self):
        resp = self.client.get("/api/debug/ev_stations")
        assert resp.status_code == 200

    def test_network_state(self):
        resp = self.client.get("/api/network_state")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "vehicles" in data

    def test_status(self):
        resp = self.client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "simulation" in data


# ---------------------------------------------------------------------------
# SUMO routes
# ---------------------------------------------------------------------------

class TestSumoRoutes:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.sm = _make_sumo_manager()
        self.state = _make_system_state()
        self.queue: list = []
        init_sumo_routes(
            sumo_manager=self.sm,
            system_state=self.state,
            vehicle_spawn_queue=self.queue,
            preload_edge_shapes=lambda: 0,
        )
        self.app.register_blueprint(sumo_bp)
        self.client = self.app.test_client()

    def test_stop_sumo_when_not_running(self):
        resp = self.client.post("/api/sumo/stop")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is False

    def test_spawn_when_not_running(self):
        resp = self.client.post(
            "/api/sumo/spawn",
            data=json.dumps({"count": 5}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is False

    def test_simulation_speed(self):
        self.state["sumo_running"] = True
        resp = self.client.post(
            "/api/simulation/speed",
            data=json.dumps({"speed": 5.0}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["speed"] == 5.0

    def test_get_ev_config(self):
        resp = self.client.get("/api/ev/config")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_update_ev_config(self):
        resp = self.client.post(
            "/api/ev/config",
            data=json.dumps({"ev_percentage": 80, "battery_min_soc": 15, "battery_max_soc": 95}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["config"]["ev_percentage"] == 80


# ---------------------------------------------------------------------------
# Grid routes
# ---------------------------------------------------------------------------

class TestGridRoutes:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        init_grid_routes(
            power_grid=_make_power_grid(),
            integrated_system=_make_integrated_system(),
            sumo_manager=_make_sumo_manager(),
            v2g_manager=_make_v2g_manager(),
            system_state=_make_system_state(),
            scenario_controller=None,
        )
        self.app.register_blueprint(grid_bp)
        self.client = self.app.test_client()

    def test_snapshot_state(self):
        resp = self.client.get("/api/snapshot/state")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "meta" in data

    def test_restore_all(self):
        resp = self.client.post("/api/restore_all")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


# ---------------------------------------------------------------------------
# V2G routes
# ---------------------------------------------------------------------------

class TestV2GRoutes:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        init_v2g_routes(
            integrated_system=_make_integrated_system(),
            sumo_manager=_make_sumo_manager(),
            v2g_manager=_make_v2g_manager(),
            system_state=_make_system_state(),
        )
        self.app.register_blueprint(v2g_bp)
        self.client = self.app.test_client()

    def test_v2g_status(self):
        resp = self.client.get("/api/v2g/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "system_metrics" in data

    def test_start_session_missing_params(self):
        resp = self.client.post(
            "/api/v2g/start_session",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is False

    def test_enable_v2g_unknown_substation(self):
        resp = self.client.post("/api/v2g/enable/NonExistent")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is False


# ---------------------------------------------------------------------------
# AI routes
# ---------------------------------------------------------------------------

class TestAIRoutes:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True

        ai_bot = MagicMock()
        ai_bot.process_message.return_value = {"text": "advice", "type": "response"}
        ai_bot.generate_system_report.return_value = {"text": "report"}
        ai_bot.get_v2g_optimization.return_value = {"text": "optimize"}
        ai_bot.get_predictions.return_value = {"text": "predictions"}
        ai_bot.get_ai_status.return_value = {"status": "ok"}

        active = MagicMock()
        active.is_available.return_value = False

        init_ai_routes(
            ai_chatbot=ai_bot,
            active_chatbot=active,
            ultra_chatbot=None,
            integrated_system=_make_integrated_system(),
            sumo_manager=_make_sumo_manager(),
            system_state=_make_system_state(),
            select_chatbot_fn=MagicMock(),
        )
        self.app.register_blueprint(ai_bp)
        self.client = self.app.test_client()

    def test_ai_advice(self):
        resp = self.client.get("/api/ai/advice?q=test")
        assert resp.status_code == 200
        assert "advice" in resp.get_json()

    def test_ai_report(self):
        resp = self.client.get("/api/ai/report")
        assert resp.status_code == 200

    def test_ai_predict(self):
        resp = self.client.post(
            "/api/ai/predict",
            data=json.dumps({"type": "demand"}),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_ai_chat_unavailable(self):
        resp = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"message": "hello"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["type"] == "error"

    def test_map_focus_status_empty(self):
        resp = self.client.get("/api/ai/map_focus_status")
        assert resp.status_code == 200
        assert resp.get_json()["has_update"] is False

    def test_ai_enhanced_status(self):
        resp = self.client.get("/api/ai/enhanced/status")
        assert resp.status_code == 200
