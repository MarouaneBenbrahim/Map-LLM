"""
Vehicle spawning helpers.

Pure functions extracted from ``manhattan_sumo_manager.ManhattanSUMOManager.spawn_vehicles``
for testability and reuse.
"""

from __future__ import annotations

import random
from typing import Tuple


def determine_vehicle_type(
    ev_percentage: float = 0.3,
) -> Tuple[str, bool]:
    """Pick a SUMO vehicle type ID and whether the vehicle is an EV.

    Returns ``(vtype_str, is_ev)`` — e.g. ``("ev_sedan", True)`` or
    ``("car", False)``.
    """
    is_ev = random.random() < ev_percentage
    if is_ev:
        vtype = "ev_sedan" if random.random() < 0.6 else "ev_suv"
    else:
        vtype = random.choice(["car", "taxi"])
    return vtype, is_ev


def compute_initial_soc(
    battery_min_soc: float = 0.2,
    battery_max_soc: float = 0.9,
) -> float:
    """Return a random initial State-of-Charge for an EV."""
    return random.uniform(battery_min_soc, battery_max_soc)


def compute_vehicle_color(is_ev: bool, initial_soc: float) -> Tuple[int, int, int, int]:
    """RGBA colour tuple used by ``traci.vehicle.setColor``."""
    if is_ev:
        if initial_soc < 0.25:
            return (255, 0, 0, 255)    # red — needs charging
        return (0, 255, 0, 255)        # green — charged
    return (255, 255, 0, 255)          # yellow — ICE vehicle


def compute_battery_capacity(vtype: str) -> int:
    """Battery capacity in Wh for SUMO's battery device."""
    if vtype == "ev_sedan":
        return 75_000
    if vtype == "ev_suv":
        return 100_000
    return 0
