"""
Manhattan Power Grid - Complete Integration

Thin application entry-point: initialises all subsystems, registers Blueprints
via ``app/``, and starts the background simulation thread.
"""

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
import os

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False

from core.power_system import ManhattanPowerGrid
from integrated_backend import ManhattanIntegratedSystem
from core.sumo_manager import ManhattanSUMOManager
from ml_engine import MLPowerGridEngine
from v2g_manager import V2GManager
from ai_chatbot import ManhattanAIChatbot
from ultra_intelligent_chatbot import initialize_ultra_intelligent_chatbot
from chatbot.factory import select_chatbot
from simulation.context import system_state, vehicle_spawn_queue
from simulation.loop import create_simulation_context, start_simulation_thread
from app import register_app_routes, register_blueprints

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()

import sumo_mgr.traci_compat as traci_compat

traci_compat.init(force_traci=os.environ.get("FORCE_TRACI", "0") == "1")

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
CORS(app)
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

# Register the perf routes (lightweight, no dependencies).
register_app_routes(app)

# ---------------------------------------------------------------------------
# System initialisation
# ---------------------------------------------------------------------------
print("=" * 60)
print("MANHATTAN POWER GRID - COMPLETE INTEGRATION")
print("Power + Traffic + Vehicles - World Class System")
print("=" * 60)

print("Initializing PyPSA power grid...")
power_grid = ManhattanPowerGrid()

# Note: Initial PyPSA loads are set by the ScenarioController via
# scenarios/default.json after it is initialized below.

print("Loading integrated distribution network...")
integrated_system = ManhattanIntegratedSystem(power_grid)

print("Initializing SUMO vehicle manager...")
sumo_manager = ManhattanSUMOManager(integrated_system)

print("Initializing V2G energy trading system...")
v2g_manager = V2GManager(integrated_system, sumo_manager)


def v2g_websocket_callback(event_type, data):
    """Emit V2G events via WebSocket."""
    if event_type == "restoration_complete":
        vehicles = []
        for vid, session in v2g_manager.active_sessions.items():
            if session.substation_id == data["substation"]:
                vehicles.append({
                    "id": vid,
                    "earnings": session.earnings,
                    "energy_delivered": session.power_delivered_kwh,
                })
        socketio.emit("v2g_restoration_complete", {
            "substation": data["substation"],
            "energy_delivered": data["energy_delivered"],
            "revenue": data["total_revenue"],
            "vehicles": vehicles,
        })
        print(f"[WebSocket] Emitted v2g_restoration_complete for {data['substation']}")


v2g_manager.register_notification_callback(v2g_websocket_callback)
print("V2G WebSocket notifications enabled")
sumo_manager.set_v2g_manager(v2g_manager)

ml_engine = MLPowerGridEngine(
    integrated_system=integrated_system, power_grid=power_grid, v2g_manager=v2g_manager
)

ai_chatbot = ManhattanAIChatbot(
    integrated_system=integrated_system, ml_engine=ml_engine, v2g_manager=v2g_manager
)

try:
    ultra_chatbot = initialize_ultra_intelligent_chatbot(
        integrated_system, ml_engine, v2g_manager, app
    )
    print("ULTRA-INTELLIGENT CHATBOT INTEGRATED")
except Exception as e:
    print(f"Ultra-Intelligent Chatbot not available: {e}")
    ultra_chatbot = None

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY) if (OPENAI_API_KEY and OpenAI) else None
except Exception as e:
    print(f"OpenAI client initialization skipped: {e}")
    openai_client = None

# Simulation context (scenario_controller and broadcast_state are set below).
simulation_context = create_simulation_context(
    power_grid=power_grid,
    integrated_system=integrated_system,
    sumo_manager=sumo_manager,
    v2g_manager=v2g_manager,
    scenario_controller=None,
    broadcast_state=None,
)

# ---------------------------------------------------------------------------
# Realistic load model and scenario controller
# ---------------------------------------------------------------------------
print("=" * 60)
print("INITIALIZING REALISTIC LOAD MODEL")
print("=" * 60)

scenario_controller = None
load_model = None
try:
    from realistic_load_model import RealisticLoadModel
    from scenario_controller import ScenarioController
    from scenario_integration import integrate_scenario_controller

    print("Initializing realistic load model with building types...")
    load_model = RealisticLoadModel(integrated_system)

    print("Initializing scenario controller...")

    _last_topo = {"version": -1}

    def broadcast_state(scenario_status):
        try:
            state = integrated_system.get_network_state()
            state["scenario"] = scenario_status
            state["sumo_running"] = system_state.get("sumo_running", False)

            # Only include cables and traffic_lights when the topology
            # has actually changed; the frontend caches the last-received
            # values for frames where they are omitted.
            topo_v = integrated_system._topo_version
            if topo_v == _last_topo["version"]:
                state.pop("cables", None)
                state.pop("traffic_lights", None)
            else:
                _last_topo["version"] = topo_v

            if system_state.get("sumo_running", False) and sumo_manager.running:
                try:
                    vehicles = sumo_manager.get_vehicle_positions_for_visualization()
                    state["vehicles"] = vehicles
                    state["vehicle_count"] = len(vehicles)

                    from sumo_mgr.traci_compat import traci as _traci
                    try:
                        pending_count = _traci.simulation.getPendingVehicles().getIDCount()
                    except Exception:
                        pending_count = 0

                    ev = gas = charging = low_bat = med_bat = high_bat = 0
                    for v in vehicles:
                        if v.get("is_ev", False):
                            ev += 1
                            bp = v.get("battery_percent", 100)
                            if bp < 20:
                                low_bat += 1
                            elif bp < 50:
                                med_bat += 1
                            else:
                                high_bat += 1
                            if v.get("is_charging", False):
                                charging += 1
                        else:
                            gas += 1

                    state["vehicle_stats"] = {
                        "active_vehicles": len(vehicles),
                        "pending_vehicles": pending_count,
                        "total_configured": len(vehicles) + pending_count,
                        "total_vehicles": len(vehicles),
                        "ev_vehicles": ev,
                        "gas_vehicles": gas,
                        "vehicles_charging": charging,
                        "vehicles_low_battery": low_bat,
                        "vehicles_medium_battery": med_bat,
                        "vehicles_high_battery": high_bat,
                    }
                except Exception as e:
                    print(f"Socket vehicle update error: {e}")

            if v2g_manager:
                try:
                    state["v2g"] = v2g_manager.get_v2g_dashboard_data()
                except Exception as e:
                    print(f"Socket V2G update error: {e}")

            from app.ai_routes import ai_map_focus_data

            if ai_map_focus_data:
                state["ai_focus"] = {"has_update": True, "focus_data": ai_map_focus_data}
            else:
                state["ai_focus"] = {"has_update": False}

            socketio.emit("system_update", state)
        except Exception as e:
            print(f"Broadcast error: {e}")

    scenario_controller = ScenarioController(
        integrated_system=integrated_system,
        load_model=load_model,
        power_grid=power_grid,
        sumo_manager=sumo_manager,
        on_update_callback=broadcast_state,
    )

    integrate_scenario_controller(app, scenario_controller, load_model)

    # Apply the default startup scenario to set initial PyPSA loads.
    try:
        scenario_controller.load_scenario_file("scenarios/default.json")
    except Exception as e:
        print(f"[WARN] Could not load default scenario: {e}")

    print("=" * 60)
    print("REALISTIC LOAD MODEL ACTIVE")
    print("SCENARIO CONTROLLER ACTIVE")
    print("AUTOMATIC FAILURE DETECTION ENABLED")
    print("=" * 60)

    simulation_context.scenario_controller = scenario_controller
    simulation_context.broadcast_state = broadcast_state
    start_simulation_thread(simulation_context)

except Exception as e:
    print(f"ERROR: Could not initialize realistic load model: {e}")

# ---------------------------------------------------------------------------
# Agentic chatbot (optional - requires OpenAI key)
# ---------------------------------------------------------------------------
agentic_chatbot = None
try:
    from agentic_tools import ToolExecutor
    from agentic_chatbot import AgenticChatbot
    from app.sumo_routes import current_ev_config

    tool_executor = ToolExecutor(
        integrated_system=integrated_system,
        v2g_manager=v2g_manager,
        sumo_manager=sumo_manager,
        power_grid=power_grid,
        system_state=system_state,
        scenario_controller=scenario_controller,
        current_ev_config=current_ev_config,
        vehicle_spawn_queue=vehicle_spawn_queue,
    )
    agentic_chatbot = AgenticChatbot(
        tool_executor=tool_executor,
        integrated_system=integrated_system,
        v2g_manager=v2g_manager,
        system_state=system_state,
        socketio=socketio,
        scenario_controller=scenario_controller,
    )
    print(f"AGENTIC CHATBOT INITIALIZED - {agentic_chatbot.get_tool_count()} tools available")
except Exception as e:
    print(f"Agentic Chatbot not available: {e}")
    import traceback
    traceback.print_exc()

active_chatbot = select_chatbot(
    agentic_chatbot=agentic_chatbot,
    ultra_chatbot=ultra_chatbot,
    ai_chatbot=ai_chatbot,
)
print(
    f"Active chatbot selected: {type(active_chatbot).__name__}"
    f" (available={active_chatbot.is_available()})"
)

# Edge shape cache for road-locked rendering.
EDGE_SHAPES: dict = {}


def preload_edge_shapes(max_edges: int | None = None) -> int:
    """Preload and cache SUMO edge shapes into EDGE_SHAPES using traci."""
    from sumo_mgr.traci_compat import traci as _traci, SUMO_AVAILABLE as _sumo_ok

    if not _sumo_ok:
        return 0
    if not (system_state.get("sumo_running") and getattr(sumo_manager, "running", False)):
        return 0
    count = 0
    try:
        edge_ids = [e for e in _traci.edge.getIDList() if not e.startswith(":")]
        if max_edges is not None:
            edge_ids = edge_ids[:max_edges]
        for edge_id in edge_ids:
            if edge_id in EDGE_SHAPES:
                continue
            try:
                shape_xy = _traci.edge.getShape(edge_id)
                edge_shape = []
                for sx, sy in shape_xy:
                    slon, slat = _traci.simulation.convertGeo(sx, sy)
                    edge_shape.append([slon, slat])
                EDGE_SHAPES[edge_id] = {"xy": shape_xy, "lonlat": edge_shape}
                count += 1
            except Exception:
                continue
    except Exception:
        return count
    return count


# ---------------------------------------------------------------------------
# Register extracted Blueprints
# ---------------------------------------------------------------------------
register_blueprints(
    app,
    power_grid=power_grid,
    integrated_system=integrated_system,
    sumo_manager=sumo_manager,
    v2g_manager=v2g_manager,
    ai_chatbot=ai_chatbot,
    active_chatbot=active_chatbot,
    ultra_chatbot=ultra_chatbot,
    system_state=system_state,
    vehicle_spawn_queue=vehicle_spawn_queue,
    scenario_controller=scenario_controller,
    preload_edge_shapes=preload_edge_shapes,
    select_chatbot_fn=select_chatbot,
)

# ---------------------------------------------------------------------------
# Main startup
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("COMPLETE SYSTEM INFORMATION:")
    print(f"  - Substations: {len(integrated_system.substations)}")
    print(f"  - Distribution Transformers: {len(integrated_system.distribution_transformers)}")
    print(f"  - Traffic Lights: {len(integrated_system.traffic_lights)}")
    print(f"  - EV Stations: {len(integrated_system.ev_stations)}")
    print(f"  - Primary Cables (13.8kV): {len(integrated_system.primary_cables)}")
    print(f"  - Secondary Cables (480V): {len(integrated_system.secondary_cables)}")
    print("=" * 60)
    print("\nStarting Complete System at http://localhost:5000")
    print("=" * 60)

    socketio.run(app, debug=False, port=5000, allow_unsafe_werkzeug=True)
