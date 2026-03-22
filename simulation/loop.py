from __future__ import annotations

import traceback
from datetime import datetime
from typing import Dict, Any

from config.ev_bus_mapping import EV_BUS_MAPPING
from .context import SimulationContext, system_state, vehicle_spawn_queue


_PERF_LATEST: Dict[str, Any] = {
    "last_updated": None,
    "avg_ms": {},
    "counts": {},
}


def get_perf_snapshot() -> Dict[str, Any]:
    """Return a lightweight snapshot of recent simulation performance metrics."""
    return dict(_PERF_LATEST)


def create_simulation_context(
    power_grid: Any,
    integrated_system: Any,
    sumo_manager: Any,
    v2g_manager: Any,
    scenario_controller: Any | None,
    broadcast_state: Any | None,
) -> SimulationContext:
    """Factory to create a SimulationContext wired to shared globals."""

    # Ensure default scenario is set once we can safely import SimulationScenario
    if system_state.get("scenario") is None:
        try:
            from core.sumo_manager import SimulationScenario

            system_state["scenario"] = SimulationScenario.MIDDAY
        except Exception:
            # Fallback to a plain string to avoid hard failure if import breaks
            system_state["scenario"] = "MIDDAY"

    return SimulationContext(
        power_grid=power_grid,
        integrated_system=integrated_system,
        sumo_manager=sumo_manager,
        v2g_manager=v2g_manager,
        scenario_controller=scenario_controller,
        broadcast_state=broadcast_state,
    )


def start_simulation_thread(ctx: SimulationContext) -> None:
    """Start the background simulation loop in a daemon thread."""
    import threading

    sim_thread = threading.Thread(target=_simulation_loop, args=(ctx,), daemon=True)
    sim_thread.start()


def _simulation_loop(ctx: SimulationContext) -> None:
    """Main simulation loop - moved from main_complete_integration.py."""
    # Local aliases for speed and readability
    power_grid = ctx.power_grid
    integrated_system = ctx.integrated_system
    sumo_manager = ctx.sumo_manager
    v2g_manager = ctx.v2g_manager
    scenario_controller = ctx.scenario_controller
    broadcast_state = ctx.broadcast_state

    # Import inside function to avoid impacting import time
    import time as time_module

    # REALISTIC TIMING CONFIGURATION
    # All intervals in SUMO steps (1 SUMO step = 0.1 simulation seconds)
    SUMO_STEP_TIME = 0.1  # seconds

    # Realistic update intervals (in seconds)
    TRAFFIC_LIGHT_CYCLE = 60
    POWER_GRID_UPDATE = 5
    EV_LOAD_UPDATE = 5
    V2G_UPDATE = 1

    # Convert to SUMO steps (multiply by 10 because 1 SUMO step = 0.1s)
    TRAFFIC_LIGHT_STEPS = int(TRAFFIC_LIGHT_CYCLE / SUMO_STEP_TIME)
    POWER_GRID_STEPS = int(POWER_GRID_UPDATE / SUMO_STEP_TIME)
    EV_LOAD_STEPS = int(EV_LOAD_UPDATE / SUMO_STEP_TIME)
    V2G_STEPS = int(V2G_UPDATE / SUMO_STEP_TIME)

    next_step_time = time_module.perf_counter()
    step_duration = SUMO_STEP_TIME

    last_ev_update = 0
    last_v2g_update = 0
    last_power_flow = 0

    perf_stats: Dict[str, list[float]] = {
        "sumo_step": [],
        "ev_update": [],
        "power_flow": [],
        "total_step": [],
    }
    last_perf_report = 0

    print("\n" + "=" * 70)
    print("REALISTIC TIMING MODE ENABLED")
    print("=" * 70)
    print(f"SUMO Traffic Step:      {SUMO_STEP_TIME}s")
    print(f"Traffic Light Cycle:    {TRAFFIC_LIGHT_CYCLE}s")
    print(f"Power Grid Update:      {POWER_GRID_UPDATE}s")
    print(f"EV Load Update:         {EV_LOAD_UPDATE}s")
    print(f"V2G State Update:       {V2G_UPDATE}s")
    print("=" * 70 + "\n")

    BROADCAST_INTERVAL = 5  # Send 1 update per 5 physics steps
    step_counter = 0

    while system_state["running"]:
        try:
            step_start = time_module.perf_counter()
            current_time = step_start

            # Skip if we're ahead of schedule (non-blocking timing)
            if current_time < next_step_time:
                time_module.sleep(0.001)
                continue

            # Traffic light phase updates
            if system_state["current_time"] % TRAFFIC_LIGHT_STEPS == 0:
                integrated_system.update_traffic_light_phases()
                if system_state["current_time"] > 0:
                    print(
                        f"[TRAFFIC] Light phase change at "
                        f"{system_state['current_time'] * SUMO_STEP_TIME:.1f}s"
                    )

            # Run SUMO step if active
            if system_state["sumo_running"] and getattr(sumo_manager, "running", False):
                sumo_start = time_module.perf_counter()

                sumo_manager.step()

                sumo_time = (time_module.perf_counter() - sumo_start) * 1000
                perf_stats["sumo_step"].append(sumo_time)

                # Socket broadcast: frame skipping
                step_counter += 1
                if (
                    step_counter % BROADCAST_INTERVAL == 0
                    and scenario_controller is not None
                    and broadcast_state is not None
                ):
                    try:
                        status = scenario_controller.get_system_status()
                        broadcast_state(status)
                    except Exception as exc:  # noqa: BLE001
                        print(f"Broadcast loop error: {exc}")

                # Async vehicle spawning
                if vehicle_spawn_queue:
                    batch_size = min(5, len(vehicle_spawn_queue))
                    for _ in range(batch_size):
                        config = vehicle_spawn_queue.pop(0)
                        try:
                            sumo_manager.spawn_vehicles(
                                count=1,
                                ev_percentage=config["ev_percentage"],
                                battery_min_soc=config["battery_min_soc"],
                                battery_max_soc=config["battery_max_soc"],
                            )
                        except Exception as exc:  # noqa: BLE001
                            print(f"[QUEUE] Spawn error: {exc}")

                # V2G updates
                if system_state["current_time"] - last_v2g_update >= V2G_STEPS:
                    if v2g_manager is not None:
                        v2g_manager.update_v2g_sessions()
                    last_v2g_update = system_state["current_time"]

                # EV load updates
                if system_state["current_time"] - last_ev_update >= EV_LOAD_STEPS:
                    ev_start = time_module.perf_counter()
                    _update_ev_power_loads(ctx)
                    ev_time = (time_module.perf_counter() - ev_start) * 1000
                    perf_stats["ev_update"].append(ev_time)
                    last_ev_update = system_state["current_time"]

                # Power flow updates
                if system_state["current_time"] - last_power_flow >= POWER_GRID_STEPS:
                    pf_start = time_module.perf_counter()
                    try:
                        power_grid.run_power_flow("dc")
                        pf_time = (time_module.perf_counter() - pf_start) * 1000
                        perf_stats["power_flow"].append(pf_time)
                        if pf_time > 100:
                            print(f"[WARNING] Power flow took {pf_time:.1f}ms")
                    except Exception as exc:  # noqa: BLE001
                        print(f"[ERROR] Power flow failed: {exc}")
                    last_power_flow = system_state["current_time"]

            system_state["current_time"] += 1

            # Track total step time
            total_time = (time_module.perf_counter() - step_start) * 1000
            perf_stats["total_step"].append(total_time)

            # Performance report every 30 seconds (300 SUMO steps)
            if system_state["current_time"] - last_perf_report >= 300:
                sim_time = system_state["current_time"] * SUMO_STEP_TIME
                if perf_stats["sumo_step"]:
                    avg_sumo = sum(perf_stats["sumo_step"][-100:]) / min(
                        100, len(perf_stats["sumo_step"])
                    )
                    avg_total = sum(perf_stats["total_step"][-100:]) / min(
                        100, len(perf_stats["total_step"])
                    )
                    if perf_stats["power_flow"]:
                        tail = perf_stats["power_flow"][-10:]
                        avg_pf = sum(tail) / max(1, len(tail))
                    else:
                        avg_pf = 0.0

                    print(f"\n[PERF] Simulation time: {sim_time:.1f}s")
                    print(
                        f"       Avg SUMO step: {avg_sumo:.1f}ms, "
                        f"Total step: {avg_total:.1f}ms"
                    )
                    print(f"       Power flow: {avg_pf:.1f}ms")

                    # Update exported perf snapshot
                    _PERF_LATEST["last_updated"] = datetime.now().isoformat()
                    _PERF_LATEST["avg_ms"] = {
                        "sumo_step": round(avg_sumo, 2),
                        "total_step": round(avg_total, 2),
                        "power_flow": round(avg_pf, 2),
                    }
                    _PERF_LATEST["counts"] = {
                        "sumo_step_samples": len(perf_stats["sumo_step"]),
                        "total_step_samples": len(perf_stats["total_step"]),
                        "power_flow_samples": len(perf_stats["power_flow"]),
                    }

                last_perf_report = system_state["current_time"]

            # Calculate next step time (compensates for processing time)
            next_step_time += step_duration / system_state["simulation_speed"]

            # If we're falling behind, reset timer
            if current_time > next_step_time + 0.5:
                next_step_time = current_time
                print(
                    f"[WARNING] Simulation running slow! "
                    f"Step took {total_time:.1f}ms (target: {step_duration * 1000:.1f}ms)"
                )

        except Exception as exc:  # noqa: BLE001
            print(f"Simulation error: {exc}")
            traceback.print_exc()
            time_module.sleep(1)
            next_step_time = time_module.perf_counter()


def _update_ev_power_loads(ctx: SimulationContext) -> None:
    """Update power grid loads based on EV charging (moved from main)."""
    power_grid = ctx.power_grid
    integrated_system = ctx.integrated_system
    sumo_manager = ctx.sumo_manager

    # Quick validation checks
    if not power_grid or not getattr(sumo_manager, "running", False):
        return

    # Prefer station manager for O(stations) performance
    charging_counts: Dict[str, int] = {}

    station_manager = getattr(sumo_manager, "station_manager", None)
    if station_manager is not None:
        for station_id, station in station_manager.stations.items():
            num_charging = len(station["vehicles_charging"])
            if num_charging > 0:
                charging_counts[station_id] = num_charging
    else:
        for vehicle in sumo_manager.vehicles.values():
            if (
                vehicle.config.is_ev
                and vehicle.assigned_ev_station
                and getattr(vehicle, "is_charging", False)
            ):
                station_id = vehicle.assigned_ev_station
                charging_counts[station_id] = charging_counts.get(station_id, 0) + 1

    total_charging_kw = 0.0
    substation_loads: Dict[str, float] = {}

    bus_name_mapping = EV_BUS_MAPPING

    for ev_id, ev_station in integrated_system.ev_stations.items():
        chargers_in_use = charging_counts.get(ev_id, 0)

        if chargers_in_use > 0:
            if chargers_in_use <= 5:
                power_per_vehicle = 150
            elif chargers_in_use <= 10:
                power_per_vehicle = 100
            elif chargers_in_use <= 15:
                power_per_vehicle = 50
            else:
                power_per_vehicle = 22

            charging_power_kw = chargers_in_use * power_per_vehicle
        else:
            charging_power_kw = 0

        total_charging_kw += charging_power_kw

        ev_station["vehicles_charging"] = chargers_in_use
        ev_station["current_load_kw"] = charging_power_kw

        substation_name = ev_station["substation"]
        substation_loads[substation_name] = substation_loads.get(substation_name, 0.0) + charging_power_kw

    pypsa_updates: Dict[str, tuple[str, float]] = {}

    for substation_name, load_kw in substation_loads.items():
        load_mw = load_kw / 1000.0

        bus_name = bus_name_mapping.get(substation_name)
        if not bus_name:
            continue

        bus_name_in_pypsa = None
        for variant in [bus_name, bus_name.replace("'", ""), bus_name.replace(" ", "_")]:
            if variant in power_grid.network.buses.index:
                bus_name_in_pypsa = variant
                break

        if not bus_name_in_pypsa:
            continue

        clean_name = substation_name.replace(" ", "_").replace("'", "")
        ev_load_name = f"EV_{clean_name}"
        pypsa_updates[ev_load_name] = (bus_name_in_pypsa, load_mw)

        if substation_name in integrated_system.substations:
            integrated_system.substations[substation_name]["ev_load_mw"] = load_mw

    for ev_load_name, (bus_name_in_pypsa, load_mw) in pypsa_updates.items():
        try:
            if ev_load_name not in power_grid.network.loads.index:
                power_grid.network.add("Load", ev_load_name, bus=bus_name_in_pypsa, p_set=load_mw)
            else:
                power_grid.network.loads.at[ev_load_name, "p_set"] = load_mw
        except Exception:
            # Silent failure for performance; logging here could be very noisy
            continue

    for substation_name in bus_name_mapping.keys():
        if substation_name not in substation_loads:
            clean_name = substation_name.replace(" ", "_").replace("'", "")
            ev_load_name = f"EV_{clean_name}"
            if ev_load_name in power_grid.network.loads.index:
                power_grid.network.loads.at[ev_load_name, "p_set"] = 0

    total_ev_load_mw = total_charging_kw / 1000.0
    # Keep a light global tracker for debugging; don't fail if missing
    prev = globals().get("previous_ev_load_mw", 0.0)
    globals()["previous_ev_load_mw"] = total_ev_load_mw
    if int(total_ev_load_mw) != int(prev):
        # Only log when the integer MW value changes to avoid spam
        print(f"[EV LOAD] Total EV load: {total_ev_load_mw:.1f} MW")

