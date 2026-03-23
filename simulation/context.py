from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


# Shared simulation state dictionaries/lists live here so they can be used
# consistently by both the simulation loop and the Flask app.

# High-level system state used throughout the app
system_state: Dict[str, Any] = {
    "running": True,
    "sumo_running": False,
    "simulation_speed": 1.0,
    "current_time": 0,
    # Default scenario is imported lazily in SimulationContext to avoid
    # circular imports with core.sumo_manager.
    "scenario": None,
    # Sustained fleet: replenish up to this many active SUMO vehicles (None = off).
    "target_vehicle_population": None,
    "sustain_ev_fraction": 0.6,
    "sustain_battery_min_soc": 0.2,
    "sustain_battery_max_soc": 0.9,
    "sustain_max_per_step": 50,
    "sustain_spawned_last_step": 0,
}

# Asynchronous vehicle spawn queue (processed inside the simulation loop)
vehicle_spawn_queue: List[Dict[str, Any]] = []


@dataclass
class SimulationContext:
    """Container for all simulation dependencies and callbacks.

    The shared mutable state objects (`system_state`, `vehicle_spawn_queue`)
    live at module level and are imported directly where needed. They are not
    dataclass fields to avoid mutable-default issues.
    """

    power_grid: Any
    integrated_system: Any
    sumo_manager: Any
    v2g_manager: Any
    scenario_controller: Optional[Any] = None
    broadcast_state: Optional[Callable[[Dict[str, Any]], None]] = None

