from __future__ import annotations

import random
from datetime import datetime

from flask import Blueprint, jsonify, request

bp = Blueprint("sumo", __name__)

_sumo_manager = None
_system_state = None
_vehicle_spawn_queue = None
_preload_edge_shapes = None
_scenario_controller = None

current_ev_config: dict = {
    "ev_percentage": 70,
    "battery_min_soc": 20,
    "battery_max_soc": 90,
    "updated_at": None,
}


def init_sumo_routes(
    sumo_manager, system_state, vehicle_spawn_queue, preload_edge_shapes, scenario_controller=None
):
    global _sumo_manager, _system_state, _vehicle_spawn_queue
    global _preload_edge_shapes, _scenario_controller
    _sumo_manager = sumo_manager
    _system_state = system_state
    _vehicle_spawn_queue = vehicle_spawn_queue
    _preload_edge_shapes = preload_edge_shapes
    _scenario_controller = scenario_controller
    current_ev_config["updated_at"] = datetime.now().isoformat()


@bp.route("/api/sumo/start", methods=["POST"])
def start_sumo():
    """Start SUMO simulation."""
    if _system_state["sumo_running"]:
        return jsonify({"success": False, "message": "SUMO already running"})

    try:
        success = _sumo_manager.start_sumo(gui=False, seed=42)
        if success:
            _system_state["sumo_running"] = True

            data = request.json or {}
            count = data.get("vehicle_count", 10)
            ev_percentage = data.get("ev_percentage", 0.7)
            battery_min_soc = data.get("battery_min_soc", 0.2)
            battery_max_soc = data.get("battery_max_soc", 0.9)

            spawned = _sumo_manager.spawn_vehicles(
                count, ev_percentage, battery_min_soc, battery_max_soc
            )

            # Update grid-side EV loads through the scenario controller
            if _scenario_controller and hasattr(_scenario_controller, "add_vehicles"):
                try:
                    _scenario_controller.add_vehicles(count)
                except Exception as sc_err:
                    print(f"[WARN] Scenario controller EV load sync skipped: {sc_err}")

            try:
                cached = _preload_edge_shapes()
                print(f"Preloaded {cached} SUMO edge shapes")
            except Exception as e:
                print(f"Edge preload skipped: {e}")

            return jsonify({
                "success": True,
                "message": "SUMO started with vehicles",
                "vehicles_spawned": spawned,
            })
        else:
            return jsonify({"success": False, "message": "Failed to start SUMO"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@bp.route("/api/sumo/stop", methods=["POST"])
def stop_sumo():
    """Stop SUMO simulation."""
    if _system_state["sumo_running"]:
        _sumo_manager.stop()
        _system_state["sumo_running"] = False
        return jsonify({"success": True, "message": "SUMO stopped"})
    return jsonify({"success": False, "message": "SUMO not running"})


@bp.route("/api/sumo/spawn", methods=["POST"])
def spawn_vehicles():
    """Spawn additional vehicles (async queue)."""
    if not _system_state["sumo_running"]:
        return jsonify({"success": False, "message": "SUMO not running"})

    data = request.json or {}
    count = data.get("count", 5)
    ev_percentage = data.get("ev_percentage", 0.7)
    battery_min_soc = data.get("battery_min_soc", 0.2)
    battery_max_soc = data.get("battery_max_soc", 0.9)

    for _ in range(count):
        _vehicle_spawn_queue.append({
            "ev_percentage": ev_percentage,
            "battery_min_soc": battery_min_soc,
            "battery_max_soc": battery_max_soc,
        })

    return (
        jsonify({
            "success": True,
            "message": f"{count} vehicles queued for spawning",
            "queued": len(_vehicle_spawn_queue),
            "total_vehicles": _sumo_manager.stats.get("total_vehicles", 0),
        }),
        202,
    )


@bp.route("/api/sumo/scenario", methods=["POST"])
def set_scenario():
    """Scenario control minimized per request. Only EV rush supported."""
    data = request.json or {}
    scenario_name = data.get("scenario", "EV_RUSH")

    if not _system_state["sumo_running"]:
        return jsonify({"success": False, "message": "SUMO not running"})

    if scenario_name == "EV_RUSH":
        if _scenario_controller and hasattr(_scenario_controller, "run_scenario"):
            try:
                _scenario_controller.run_scenario("rush_hour_stress_test")
            except Exception as sc_err:
                print(f"[WARN] Scenario controller run_scenario failed: {sc_err}")
        spawned = _sumo_manager.spawn_vehicles(30, 0.9)
        return jsonify({"success": True, "scenario": "EV_RUSH", "spawned": spawned})

    return jsonify({"success": False, "message": "Only EV_RUSH is supported now"})


@bp.route("/api/simulation/speed", methods=["POST"])
def set_simulation_speed():
    """Set simulation speed."""
    data = request.json or {}
    speed = data.get("speed", 1.0)
    _system_state["simulation_speed"] = max(0.1, min(10.0, speed))
    return jsonify({"success": True, "speed": _system_state["simulation_speed"]})


@bp.route("/api/ev/config", methods=["POST"])
def update_ev_config():
    """Update EV configuration settings."""
    try:
        data = request.json or {}
        ev_percentage = max(0, min(100, data.get("ev_percentage", 70)))
        battery_min_soc = max(1, min(100, data.get("battery_min_soc", 20)))
        battery_max_soc = max(1, min(100, data.get("battery_max_soc", 90)))

        if battery_min_soc >= battery_max_soc:
            battery_min_soc = battery_max_soc - 1

        current_ev_config.update({
            "ev_percentage": ev_percentage,
            "battery_min_soc": battery_min_soc,
            "battery_max_soc": battery_max_soc,
            "updated_at": datetime.now().isoformat(),
        })

        if _sumo_manager and _sumo_manager.running:
            _sumo_manager.ev_percentage = ev_percentage / 100
            _sumo_manager.battery_min_soc = battery_min_soc / 100
            _sumo_manager.battery_max_soc = battery_max_soc / 100

        print(f"EV Configuration Updated:")
        print(f"   EV Percentage: {ev_percentage}%")
        print(f"   Battery SOC Range: {battery_min_soc}% - {battery_max_soc}%")

        return jsonify({
            "success": True,
            "message": "EV configuration updated successfully",
            "config": current_ev_config,
        })
    except Exception as e:
        print(f"[ERROR] EV config update error: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to update EV configuration: {e}",
        }), 500


@bp.route("/api/ev/config", methods=["GET"])
def get_ev_config():
    """Get current EV configuration."""
    if not current_ev_config.get("updated_at"):
        current_ev_config["updated_at"] = datetime.now().isoformat()
    return jsonify({"success": True, "config": current_ev_config})


@bp.route("/api/test/ev_rush", methods=["POST"])
def test_ev_rush():
    """Test scenario: spawn many low-battery EVs."""
    if not _system_state["sumo_running"]:
        return jsonify({"success": False, "message": "Start SUMO first"})

    spawned = 0
    for i in range(30):
        vehicle_id = f"test_ev_{i}"
        try:
            import traci

            edges = [e for e in traci.edge.getIDList() if not e.startswith(":")]
            if len(edges) >= 2:
                origin = edges[i % len(edges)]
                dest = edges[(i + 10) % len(edges)]

                route = traci.simulation.findRoute(origin, dest)
                if route and route.edges:
                    route_id = f"test_route_{i}"
                    traci.route.add(route_id, route.edges)
                    traci.vehicle.add(vehicle_id, route_id, typeID="ev_sedan", depart="now")
                    traci.vehicle.setColor(vehicle_id, (255, 0, 0, 255))
                    traci.vehicle.setMaxSpeed(vehicle_id, 40)

                    battery = 75000 * random.uniform(0.10, 0.20)
                    traci.vehicle.setParameter(
                        vehicle_id, "device.battery.actualBatteryCapacity", str(battery)
                    )
                    spawned += 1
        except Exception:
            pass

    return jsonify({"success": True, "message": f"Spawned {spawned} low-battery EVs for testing"})
