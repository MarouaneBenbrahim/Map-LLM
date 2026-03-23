from __future__ import annotations

import time
from datetime import datetime

from flask import Blueprint, jsonify, request

bp = Blueprint("v2g", __name__)

_integrated_system = None
_sumo_manager = None
_v2g_manager = None
_system_state = None


def init_v2g_routes(integrated_system, sumo_manager, v2g_manager, system_state):
    global _integrated_system, _sumo_manager, _v2g_manager, _system_state
    _integrated_system = integrated_system
    _sumo_manager = sumo_manager
    _v2g_manager = v2g_manager
    _system_state = system_state


@bp.route("/api/v2g/enable/<substation>", methods=["POST"])
def enable_v2g(substation):
    """Enable V2G for a failed substation with better feedback."""
    if substation not in _integrated_system.substations:
        return jsonify({"success": False, "message": f"Substation {substation} not found"})

    sub_data = _integrated_system.substations[substation]
    if sub_data["operational"]:
        return jsonify({
            "success": False,
            "message": f"{substation} is operational - V2G not needed",
        })

    success = _v2g_manager.enable_v2g_for_substation(substation)

    if success:
        power_needed_mw = sub_data["load_mw"]
        rate = _v2g_manager.get_current_rate(substation)
        energy_needed = _v2g_manager.substation_energy_required.get(substation, 50)
        total_value = energy_needed * rate
        vehicles_needed = max(2, int(energy_needed / 30) + 1)

        return jsonify({
            "success": True,
            "message": f"V2G enabled for {substation}",
            "power_needed_mw": power_needed_mw,
            "energy_needed_kwh": energy_needed,
            "rate_per_kwh": rate,
            "total_restoration_value": total_value,
            "vehicles_needed": vehicles_needed,
            "earnings_per_vehicle": total_value / vehicles_needed,
        })
    return jsonify({"success": False, "message": f"Failed to enable V2G for {substation}"})


@bp.route("/api/v2g/disable/<substation>", methods=["POST"])
def disable_v2g(substation):
    """Disable V2G for a substation."""
    _v2g_manager.disable_v2g_for_substation(substation)
    return jsonify({"success": True})


@bp.route("/api/v2g/release_vehicles/<substation>", methods=["POST"])
def release_v2g_vehicles(substation):
    """Force release all V2G vehicles from this substation's charging stations."""
    try:
        print(f"\n[API RELEASE] Force releasing V2G vehicles for {substation}")

        substation_ev_stations = [
            ev_id
            for ev_id, ev_data in _integrated_system.ev_stations.items()
            if ev_data.get("substation") == substation
        ]

        vehicles_to_release = [
            vid
            for vid, session in list(_v2g_manager.active_sessions.items())
            if session.substation_id == substation or session.station_id in substation_ev_stations
        ]

        released_count = 0
        for vehicle_id in vehicles_to_release:
            if vehicle_id in _v2g_manager.active_sessions:
                session = _v2g_manager.active_sessions[vehicle_id]
                session.end_time = datetime.now()
                session.locked_at_station = False
                del _v2g_manager.active_sessions[vehicle_id]

            if vehicle_id in _v2g_manager.v2g_locked_vehicles:
                _v2g_manager.v2g_locked_vehicles.remove(vehicle_id)

            if vehicle_id in _v2g_manager.pending_v2g_vehicles:
                _v2g_manager.pending_v2g_vehicles.remove(vehicle_id)

            if vehicle_id in _sumo_manager.vehicles:
                vehicle = _sumo_manager.vehicles[vehicle_id]
                vehicle.in_v2g_session = False
                vehicle.v2g_lock = False
                vehicle.is_charging = False
                vehicle.charge_start_time = None

            released_count += 1

        print(f"[API RELEASE] Released {released_count} vehicles")
        return jsonify({"success": True, "released": released_count, "substation": substation})

    except Exception as e:
        print(f"[API ERROR] Failed to release V2G vehicles: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/v2g/status")
def v2g_status():
    """Get V2G system status with real-time updates."""
    v2g_data = _v2g_manager.get_v2g_dashboard_data()

    for substation_name in v2g_data["enabled_substations"]:
        if substation_name in _integrated_system.substations:
            substation = _integrated_system.substations[substation_name]
            base_power_need_mw = substation["load_mw"]

            active_v2g_power_mw = sum(
                0.25
                for vehicle in v2g_data["active_vehicles"]
                if vehicle["substation"] == substation_name
            )

            remaining_power_need_mw = max(0, base_power_need_mw - active_v2g_power_mw)

            if "power_needs" not in v2g_data:
                v2g_data["power_needs"] = {}
            v2g_data["power_needs"][substation_name] = remaining_power_need_mw * 1000

            v2g_data.setdefault("real_time_metrics", {})[substation_name] = {
                "base_load_mw": base_power_need_mw,
                "v2g_providing_mw": active_v2g_power_mw,
                "remaining_need_mw": remaining_power_need_mw,
                "vehicles_discharging": sum(
                    1
                    for v in v2g_data["active_sessions"]
                    if v["substation"] == substation_name
                ),
                "restoration_progress": (
                    v2g_data.get("energy_delivered", {}).get(substation_name, 0)
                    / max(v2g_data.get("energy_required", {}).get(substation_name, 1), 1)
                )
                * 100,
            }

    v2g_data["system_metrics"] = {
        "total_v2g_power_mw": len(v2g_data["active_sessions"]) * 0.25,
        "total_substations_needing_power": len(v2g_data["enabled_substations"]),
        "total_power_deficit_mw": sum(
            _integrated_system.substations[s]["load_mw"]
            for s in v2g_data["enabled_substations"]
            if s in _integrated_system.substations
        ),
        "effective_power_deficit_mw": sum(
            max(
                0,
                _integrated_system.substations[s]["load_mw"]
                - sum(0.25 for v in v2g_data["active_sessions"] if v["substation"] == s),
            )
            for s in v2g_data["enabled_substations"]
            if s in _integrated_system.substations
        ),
    }

    if v2g_data.get("active_sessions"):
        print(
            f"[V2G STATUS] Active sessions: {v2g_data['active_sessions']}"
        )
        metrics = v2g_data["system_metrics"]
        print(
            f"[V2G STATUS] Total V2G power: {metrics['total_v2g_power_mw']:.2f} MW"
        )
        print(
            f"[V2G STATUS] Power deficit: {metrics['total_power_deficit_mw']:.2f} MW"
            f" -> {metrics['effective_power_deficit_mw']:.2f} MW"
        )

    return jsonify(v2g_data)


@bp.route("/api/v2g/start_session", methods=["POST"])
def start_v2g_session():
    """Manually start V2G session for testing."""
    data = request.json or {}
    vehicle_id = data.get("vehicle_id")
    station_id = data.get("station_id")
    substation_id = data.get("substation_id")

    if not all([vehicle_id, station_id, substation_id]):
        return jsonify({"success": False, "message": "Missing parameters"})

    success = _v2g_manager.start_v2g_session(vehicle_id, station_id, substation_id)
    return jsonify({"success": success})


@bp.route("/api/v2g/test", methods=["POST"])
def test_v2g_scenario():
    """Test V2G with a complete scenario."""
    try:
        times_square = _integrated_system.substations.get("Times Square")
        if times_square and times_square["operational"]:
            _integrated_system.simulate_substation_failure("Times Square")
            time.sleep(0.5)

        success = _v2g_manager.enable_v2g_for_substation("Times Square")
        if not success:
            return jsonify({
                "success": False,
                "message": "Could not enable V2G for Times Square",
            })

        routed_vehicles = []
        if _sumo_manager.running:
            from sumo_mgr.traci_compat import traci  # noqa: F811

            for vehicle in _sumo_manager.vehicles.values():
                if (
                    vehicle.config.is_ev
                    and vehicle.config.current_soc >= 0.60
                    and not hasattr(vehicle, "in_v2g_session")
                    and len(routed_vehicles) < 3
                ):
                    vehicle.config.current_soc = 0.85
                    _v2g_manager._route_to_v2g_station(vehicle, "Times Square")
                    routed_vehicles.append(vehicle.id)

        return jsonify({
            "success": True,
            "message": "V2G test scenario started",
            "substation": "Times Square",
            "power_deficit_mw": times_square["load_mw"],
            "rate_per_kwh": _v2g_manager.get_current_rate("Times Square"),
            "vehicles_routed": routed_vehicles,
            "expected_duration": "15-30 seconds",
            "expected_earnings_per_vehicle": "$150-300",
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Test failed: {e}"})
