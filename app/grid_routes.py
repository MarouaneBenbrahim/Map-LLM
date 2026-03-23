from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request

bp = Blueprint("grid", __name__)

_power_grid = None
_integrated_system = None
_sumo_manager = None
_v2g_manager = None
_system_state = None
_scenario_controller = None


def init_grid_routes(
    power_grid,
    integrated_system,
    sumo_manager,
    v2g_manager,
    system_state,
    scenario_controller,
):
    global _power_grid, _integrated_system, _sumo_manager
    global _v2g_manager, _system_state, _scenario_controller
    _power_grid = power_grid
    _integrated_system = integrated_system
    _sumo_manager = sumo_manager
    _v2g_manager = v2g_manager
    _system_state = system_state
    _scenario_controller = scenario_controller


def _collect_comprehensive_state() -> dict:
    """Collect a rich system state dict used by both snapshot and report APIs."""
    state = _integrated_system.get_network_state()

    if _system_state.get("sumo_running") and _sumo_manager and _sumo_manager.running:
        state["vehicle_stats"] = _sumo_manager.get_statistics()
    else:
        state["vehicle_stats"] = {}

    if _v2g_manager:
        state["v2g"] = _v2g_manager.get_v2g_dashboard_data()
    else:
        state["v2g"] = {}

    if _scenario_controller:
        state["scenario"] = _scenario_controller.get_system_status()
    else:
        state["scenario"] = {}

    state["sumo_running"] = _system_state.get("sumo_running", False)

    stats = state.get("statistics", {})
    subs = state.get("substations", [])
    v2g_data = state.get("v2g", {})
    v_stats = state.get("vehicle_stats", {})

    total_capacity = sum(s.get("capacity_mva", 0) for s in subs)
    total_load = stats.get("total_load_mw", state.get("total_load_mw", 0))
    op_subs = sum(1 for s in subs if s.get("operational"))
    total_subs = len(subs)
    total_vehicles = v_stats.get("active_vehicles", v_stats.get("total_vehicles", 0))
    ev_count = v_stats.get("ev_vehicles", 0)

    state["kpis"] = {
        "capacity_utilization_pct": (
            round(total_load / total_capacity * 100, 1) if total_capacity else 0
        ),
        "grid_health_pct": round(op_subs / total_subs * 100, 1) if total_subs else 100,
        "ev_adoption_pct": round(ev_count / total_vehicles * 100, 1) if total_vehicles else 0,
        "v2g_participation_pct": (
            round(v2g_data.get("active_sessions_count", 0) / max(ev_count, 1) * 100, 1)
            if ev_count
            else 0
        ),
        "avg_substation_load_pct": (
            round(total_load / total_capacity * 100, 1) if total_capacity else 0
        ),
        "cable_integrity_pct": round(
            (stats.get("operational_primary_cables", 0) + stats.get("operational_secondary_cables", 0))
            / max(
                stats.get("total_primary_cables", 0) + stats.get("total_secondary_cables", 0), 1
            )
            * 100,
            1,
        ),
        "vehicles_charging_pct": (
            round(v_stats.get("vehicles_charging", 0) / max(total_vehicles, 1) * 100, 1)
            if total_vehicles
            else 0
        ),
    }

    return state


@bp.route("/api/fail/<substation>", methods=["POST"])
def fail_substation(substation):
    """Trigger substation failure affecting traffic lights and EV stations."""
    impact = _integrated_system.simulate_substation_failure(substation)
    _power_grid.trigger_failure("substation", substation)

    if _system_state["sumo_running"] and _sumo_manager.running:
        _sumo_manager.update_traffic_lights()

        if hasattr(_sumo_manager, "handle_blackout_traffic_lights"):
            _sumo_manager.handle_blackout_traffic_lights([substation])

        for ev_id, ev_station in _integrated_system.ev_stations.items():
            if ev_station["substation"] == substation:
                ev_station["operational"] = False

                if ev_id in _sumo_manager.ev_stations_sumo:
                    _sumo_manager.ev_stations_sumo[ev_id]["available"] = 0

                if hasattr(_sumo_manager, "station_manager") and _sumo_manager.station_manager:
                    if ev_id in _sumo_manager.station_manager.stations:
                        _sumo_manager.station_manager.stations[ev_id]["operational"] = False
                        released = _sumo_manager.station_manager.handle_blackout(substation)
                        if released:
                            for veh_id in released:
                                if (
                                    hasattr(_sumo_manager, "vehicles")
                                    and veh_id in _sumo_manager.vehicles
                                ):
                                    v = _sumo_manager.vehicles[veh_id]
                                    if hasattr(v, "is_charging"):
                                        v.is_charging = False
                                    if hasattr(v, "assigned_ev_station"):
                                        v.assigned_ev_station = None

        if hasattr(_sumo_manager, "vehicles") and _sumo_manager.vehicles:
            for v in _sumo_manager.vehicles.values():
                if hasattr(v, "assigned_ev_station") and v.assigned_ev_station:
                    sid = v.assigned_ev_station
                    if (
                        sid in _integrated_system.ev_stations
                        and _integrated_system.ev_stations[sid]["substation"] == substation
                    ):
                        v.assigned_ev_station = None
                        if hasattr(v, "is_charging"):
                            v.is_charging = False

    print(f"\nPOWER SUBSTATION FAILURE: {substation}")
    print(f"   - Traffic lights: Set to YELLOW (caution mode)")
    print(f"   - EV stations affected: {impact.get('ev_stations_affected', 0)}")
    print(f"   - Load lost: {impact.get('load_lost_mw', 0):.1f} MW")

    return jsonify(impact)


@bp.route("/api/fail/station/<station_id>", methods=["POST"])
def fail_ev_station(station_id):
    """Trigger individual EV station failure."""
    if not _system_state["sumo_running"]:
        return jsonify({"success": False, "message": "Start SUMO first"})

    if station_id not in _integrated_system.ev_stations:
        return jsonify({"success": False, "message": f"Station {station_id} not found"})

    released_vehicles = []
    if hasattr(_sumo_manager, "station_manager") and _sumo_manager.station_manager:
        released_vehicles = _sumo_manager.station_manager.handle_station_failure(station_id)
        if released_vehicles:
            for veh_id in released_vehicles:
                if hasattr(_sumo_manager, "vehicles") and veh_id in _sumo_manager.vehicles:
                    v = _sumo_manager.vehicles[veh_id]
                    if hasattr(v, "is_charging"):
                        v.is_charging = False
                    if hasattr(v, "assigned_ev_station"):
                        v.assigned_ev_station = None

    if hasattr(_sumo_manager, "vehicles") and _sumo_manager.vehicles:
        for v in _sumo_manager.vehicles.values():
            if hasattr(v, "assigned_ev_station") and v.assigned_ev_station == station_id:
                v.assigned_ev_station = None
                if hasattr(v, "is_charging"):
                    v.is_charging = False

    _integrated_system.ev_stations[station_id]["operational"] = False
    if station_id in _sumo_manager.ev_stations_sumo:
        _sumo_manager.ev_stations_sumo[station_id]["available"] = 0

    station_name = _integrated_system.ev_stations[station_id]["name"]
    return jsonify({
        "success": True,
        "station_id": station_id,
        "station_name": station_name,
        "released_vehicles": released_vehicles,
        "message": f"Station {station_name} failed - {len(released_vehicles)} vehicles released",
    })


@bp.route("/api/restore/<substation>", methods=["POST"])
def restore_substation(substation):
    """Restore substation."""
    success = _integrated_system.restore_substation(substation)

    restoration_data = {
        "substation": substation,
        "success": success,
        "lights_restored": 0,
        "ev_stations_restored": 0,
        "timestamp": datetime.now().isoformat(),
    }

    if success:
        _power_grid.restore_component("substation", substation)
        print(f"[RESTORE] Disabling V2G for {substation} and releasing vehicles...")
        _v2g_manager.disable_v2g_for_substation(substation)

        if _system_state["sumo_running"] and _sumo_manager.running:
            lights_before = sum(
                1 for light in _integrated_system.traffic_lights.values()
                if light.get("powered", False)
            )
            _sumo_manager.update_traffic_lights()
            lights_after = sum(
                1 for light in _integrated_system.traffic_lights.values()
                if light.get("powered", False)
            )
            restoration_data["lights_restored"] = lights_after - lights_before

            ev_stations_restored = 0
            for ev_id, ev_station in _integrated_system.ev_stations.items():
                if ev_station["substation"] == substation:
                    ev_station["operational"] = True
                    ev_stations_restored += 1

                    if ev_id in _sumo_manager.ev_stations_sumo:
                        _sumo_manager.ev_stations_sumo[ev_id]["available"] = ev_station["chargers"]

                    if (
                        hasattr(_sumo_manager, "station_manager")
                        and _sumo_manager.station_manager
                    ):
                        if ev_id in _sumo_manager.station_manager.stations:
                            _sumo_manager.station_manager.stations[ev_id]["operational"] = True
                            print(f"   Restored {ev_station['name']} ONLINE")

            restoration_data["ev_stations_restored"] = ev_stations_restored

    return jsonify(restoration_data)


@bp.route("/api/restore/station/<station_id>", methods=["POST"])
def restore_ev_station(station_id):
    """Restore individual EV station."""
    if not _system_state["sumo_running"]:
        return jsonify({"success": False, "message": "Start SUMO first"})

    if station_id not in _integrated_system.ev_stations:
        return jsonify({"success": False, "message": f"Station {station_id} not found"})

    success = False
    if hasattr(_sumo_manager, "station_manager") and _sumo_manager.station_manager:
        success = _sumo_manager.station_manager.restore_station(station_id)

    _integrated_system.ev_stations[station_id]["operational"] = True
    if station_id in _sumo_manager.ev_stations_sumo:
        station_info = _integrated_system.ev_stations[station_id]
        _sumo_manager.ev_stations_sumo[station_id]["available"] = station_info["chargers"]

    station_name = _integrated_system.ev_stations[station_id]["name"]
    return jsonify({
        "success": success,
        "station_id": station_id,
        "station_name": station_name,
    })


@bp.route("/api/snapshot/state")
def snapshot_state():
    """Return comprehensive system state as JSON (server-side snapshot)."""
    try:
        state = _collect_comprehensive_state()
        state["meta"] = {
            "snapshot_id": f"SNAP-{int(datetime.now().timestamp() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "generated_by": "Manhattan Grid Control - Server",
        }
        return jsonify(state)
    except Exception as e:
        print(f"Snapshot state failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/report/generate", methods=["POST"])
def generate_report():
    """Generate a comprehensive system status report PDF with optional AI analysis."""
    try:
        data = request.json or {}
        notes = data.get("notes", None)
        screenshot_b64 = data.get("screenshot_base64", None)

        state = _collect_comprehensive_state()

        from report_generator import ReportGenerator

        generator = ReportGenerator()
        report_url = generator.generate_status_report(
            state, notes=notes, screenshot_base64=screenshot_b64
        )

        return jsonify({"success": True, "url": report_url, "message": "Report generated successfully"})
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Report generation failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/restore_all", methods=["POST"])
def restore_all():
    """Restore all substations."""
    restored_count = 0

    for sub_name in _integrated_system.substations.keys():
        _integrated_system.restore_substation(sub_name)
        _power_grid.restore_component("substation", sub_name)
        print(f"[RESTORE ALL] Disabling V2G for {sub_name} and releasing vehicles...")
        _v2g_manager.disable_v2g_for_substation(sub_name)
        restored_count += 1

    if _system_state["sumo_running"] and _sumo_manager.running:
        _sumo_manager.update_traffic_lights()
        for ev_id, ev_station in _integrated_system.ev_stations.items():
            if ev_id in _sumo_manager.ev_stations_sumo:
                _sumo_manager.ev_stations_sumo[ev_id]["available"] = ev_station["chargers"]

    return jsonify({
        "success": True,
        "message": f"All {restored_count} substations restored",
        "restored_count": restored_count,
    })


@bp.route("/api/test/station_failure", methods=["POST"])
def test_station_failure_scenario():
    """Test EV station failure scenario."""
    if not _system_state["sumo_running"]:
        return jsonify({"success": False, "message": "Start SUMO first"})

    test_station = None
    for station_id, station in _integrated_system.ev_stations.items():
        if station["operational"] and station["vehicles_charging"] > 0:
            test_station = station_id
            break

    if not test_station:
        for station_id, station in _integrated_system.ev_stations.items():
            if station["operational"]:
                test_station = station_id
                break

    if not test_station:
        return jsonify({
            "success": False,
            "message": "No operational stations available for testing",
        })

    released_vehicles = []
    if hasattr(_sumo_manager, "station_manager") and _sumo_manager.station_manager:
        released_vehicles = _sumo_manager.station_manager.handle_station_failure(test_station)

    _integrated_system.ev_stations[test_station]["operational"] = False
    if test_station in _sumo_manager.ev_stations_sumo:
        _sumo_manager.ev_stations_sumo[test_station]["available"] = 0

    station_name = _integrated_system.ev_stations[test_station]["name"]
    return jsonify({
        "success": True,
        "test_station": test_station,
        "station_name": station_name,
        "released_vehicles": released_vehicles,
        "message": (
            f"Station failure test: {station_name} failed"
            f" - {len(released_vehicles)} vehicles released"
        ),
        "instructions": (
            f"Watch as vehicles at {station_name} stop charging and redirect to other stations"
            " if they still need charging."
        ),
    })
