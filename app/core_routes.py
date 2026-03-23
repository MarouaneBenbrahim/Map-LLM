from __future__ import annotations

import io
import json
import os
from datetime import datetime

from flask import Blueprint, jsonify, render_template_string, request, send_file

bp = Blueprint("core", __name__)

_power_grid = None
_integrated_system = None
_sumo_manager = None
_v2g_manager = None
_system_state = None


def init_core_routes(
    power_grid,
    integrated_system,
    sumo_manager,
    v2g_manager,
    system_state,
):
    global _power_grid, _integrated_system, _sumo_manager, _v2g_manager, _system_state
    _power_grid = power_grid
    _integrated_system = integrated_system
    _sumo_manager = sumo_manager
    _v2g_manager = v2g_manager
    _system_state = system_state


def _load_html_template():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Error: index.html file not found"


@bp.route("/")
def index():
    """Serve complete dashboard with all features."""
    return render_template_string(_load_html_template())


@bp.route("/api/config")
def get_config():
    """Serve client-side configuration (Mapbox token, etc.) from environment."""
    return jsonify({"mapbox_token": os.environ.get("MAPBOX_TOKEN", "")})


@bp.route("/api/debug/buses")
def debug_buses():
    """Show all bus names in PyPSA."""
    buses_13kv = [b for b in _power_grid.network.buses.index if "13.8kV" in b]
    substations = list(_integrated_system.substations.keys())

    return jsonify({
        "pypsa_buses_13kv": buses_13kv,
        "integrated_substations": substations,
        "mapping_check": {
            sub: f"{sub.replace(' ', '_')}_13.8kV" in _power_grid.network.buses.index
            for sub in substations
        },
    })


@bp.route("/api/debug/pypsa")
def debug_pypsa():
    """Debug PyPSA network state."""
    debug_info = {
        "buses": list(_power_grid.network.buses.index),
        "loads": {},
        "generators": {},
        "total_load": 0,
        "total_generation": 0,
    }

    for load_name in _power_grid.network.loads.index:
        load_value = _power_grid.network.loads.at[load_name, "p_set"]
        debug_info["loads"][load_name] = float(load_value)
        debug_info["total_load"] += float(load_value)

    for gen_name in _power_grid.network.generators.index:
        gen_p = _power_grid.network.generators.at[gen_name, "p_nom"]
        debug_info["generators"][gen_name] = float(gen_p)
        debug_info["total_generation"] += float(gen_p)

    if hasattr(_power_grid.network, "loads_t") and hasattr(_power_grid.network.loads_t, "p"):
        debug_info["loads_t_sum"] = float(_power_grid.network.loads_t.p.sum().sum())
        debug_info["loads_t_shape"] = _power_grid.network.loads_t.p.shape

    return jsonify(debug_info)


@bp.route("/api/debug/ev_stations")
def debug_ev_stations():
    """Debug endpoint to check EV station status."""
    status = {}
    for ev_id, ev_station in _integrated_system.ev_stations.items():
        status[ev_id] = {
            "name": ev_station["name"],
            "substation": ev_station["substation"],
            "operational": ev_station["operational"],
            "substation_operational": _integrated_system.substations[ev_station["substation"]][
                "operational"
            ],
            "vehicles_charging": ev_station.get("vehicles_charging", 0),
            "current_load_kw": ev_station.get("current_load_kw", 0),
        }
    return jsonify(status)


@bp.route("/api/export-state")
def export_state():
    """Export the full system state as a downloadable JSON file."""
    try:
        state = _integrated_system.get_network_state()
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "system_state": state,
            "version": "1.0.0",
            "stats": {
                "vehicles": len(_sumo_manager.vehicles) if _sumo_manager.running else 0,
                "substations_online": len([
                    s
                    for s in _integrated_system.substations.values()
                    if s.get("operational", True)
                ]),
                "ev_stations_online": len([
                    s
                    for s in _integrated_system.ev_stations.values()
                    if s.get("operational", True)
                ]),
            },
        }
        mem = io.BytesIO()
        mem.write(json.dumps(export_data, indent=2).encode("utf-8"))
        mem.seek(0)
        return send_file(
            mem,
            mimetype="application/json",
            as_attachment=True,
            download_name=f"manhattan_grid_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/network_state")
def get_network_state():
    """Get complete network state including vehicles."""
    state = _integrated_system.get_network_state()

    if _system_state["sumo_running"] and _sumo_manager.running:
        vehicles = []
        station_charging_counts: dict = {}
        station_queued_counts: dict = {}

        try:
            from sumo_mgr.traci_compat import traci

            active_vehicle_ids = set(traci.vehicle.getIDList())
            for vehicle in _sumo_manager.vehicles.values():
                if vehicle.id not in active_vehicle_ids:
                    continue
                try:
                    x, y = traci.vehicle.getPosition(vehicle.id)
                    lon, lat = traci.simulation.convertGeo(x, y)
                    edge_id = traci.vehicle.getRoadID(vehicle.id)

                    if getattr(vehicle, "is_charging", False) and vehicle.assigned_ev_station:
                        station_charging_counts[vehicle.assigned_ev_station] = (
                            station_charging_counts.get(vehicle.assigned_ev_station, 0) + 1
                        )
                    if getattr(vehicle, "is_queued", False) and vehicle.assigned_ev_station:
                        station_queued_counts[vehicle.assigned_ev_station] = (
                            station_queued_counts.get(vehicle.assigned_ev_station, 0) + 1
                        )

                    vehicles.append({
                        "id": vehicle.id,
                        "lat": lat,
                        "lon": lon,
                        "type": vehicle.config.vtype.value,
                        "speed_kmh": round(vehicle.speed * 3.6, 1),
                        "battery_percent": (
                            round(vehicle.config.current_soc * 100)
                            if vehicle.config.is_ev
                            else 100
                        ),
                        "is_charging": getattr(vehicle, "is_charging", False),
                        "is_queued": getattr(vehicle, "is_queued", False),
                        "is_v2g_active": vehicle.id in _v2g_manager.active_sessions,
                        "is_ev": vehicle.config.is_ev,
                        "assigned_station": vehicle.assigned_ev_station,
                        "edge_id": edge_id if edge_id and not edge_id.startswith(":") else None,
                    })
                except Exception:
                    continue
        except Exception:
            pass

        state["vehicles"] = vehicles
        state["vehicle_stats"] = _sumo_manager.get_statistics()

        for ev_station in state["ev_stations"]:
            ev_station["vehicles_charging"] = station_charging_counts.get(ev_station["id"], 0)
            ev_station["vehicles_queued"] = station_queued_counts.get(ev_station["id"], 0)
    else:
        state["vehicles"] = []
        state["vehicle_stats"] = {}

    if _v2g_manager:
        state["v2g"] = _v2g_manager.get_v2g_dashboard_data()

    return jsonify(state)


@bp.route("/api/status")
def get_status():
    """Get complete system status."""
    power_status = _power_grid.get_system_status()

    for sub_name in _integrated_system.substations.keys():
        if sub_name in power_status.get("substations", {}):
            integrated_sub = _integrated_system.substations[sub_name]
            power_status["substations"][sub_name]["operational"] = integrated_sub.get(
                "operational", True
            )
            power_status["substations"][sub_name]["load_mw"] = integrated_sub.get("load_mw", 0)
            power_status["substations"][sub_name]["lat"] = integrated_sub.get("lat", 0)
            power_status["substations"][sub_name]["lon"] = integrated_sub.get("lon", 0)

    if _system_state["sumo_running"] and _sumo_manager.running:
        vehicle_stats = _sumo_manager.get_statistics()
        power_status["vehicles"] = {
            "total": vehicle_stats["total_vehicles"],
            "active": len(_sumo_manager.vehicles),
            "evs": vehicle_stats["ev_vehicles"],
            "charging": vehicle_stats["vehicles_charging"],
            "avg_speed_kmh": round(vehicle_stats["avg_speed_mps"] * 3.6, 1),
            "energy_consumed_kwh": round(vehicle_stats["total_energy_consumed_kwh"], 2),
        }
    else:
        power_status["vehicles"] = {
            "total": 0,
            "active": 0,
            "evs": 0,
            "charging": 0,
            "avg_speed_kmh": 0,
            "energy_consumed_kwh": 0,
        }

    power_status["simulation"] = {
        "sumo_running": _system_state["sumo_running"],
        "speed": _system_state["simulation_speed"],
        "scenario": _system_state["scenario"].value,
    }

    return jsonify(power_status)
