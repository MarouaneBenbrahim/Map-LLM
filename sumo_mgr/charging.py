"""
EV charging / station selection helpers.

Pure functions extracted from ``manhattan_sumo_manager.ManhattanSUMOManager``
for testability and reuse.
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Tuple


def select_charging_power_kw(chargers_in_use: int) -> int:
    """Return per-vehicle charging power (kW) based on current occupancy.

    The tiered logic mirrors the original ``_update_ev_power_loads`` in the
    simulation loop:

    * 1–5 vehicles  → 150 kW (DC fast)
    * 6–10          → 100 kW
    * 11–15         →  50 kW
    * >15           →  22 kW (AC Level 2)
    """
    if chargers_in_use <= 0:
        return 0
    if chargers_in_use <= 5:
        return 150
    if chargers_in_use <= 10:
        return 100
    if chargers_in_use <= 15:
        return 50
    return 22


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    """Approximate distance in metres between two WGS-84 points."""
    R = 6_371_000  # Earth radius in metres
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_station(
    vehicle_lat: float,
    vehicle_lon: float,
    stations: Dict[str, dict],
    ev_stations_info: Dict[str, dict],
    excluded: list,
    max_occupancy: int = 8,
) -> Optional[str]:
    """Find the nearest available charging station.

    Parameters
    ----------
    vehicle_lat, vehicle_lon:
        Current vehicle position in WGS-84.
    stations:
        Station-manager ``stations`` dict (keys are station IDs, values have
        ``operational`` and ``vehicles_charging`` entries).
    ev_stations_info:
        Integrated-system ``ev_stations`` dict (carries ``lat``/``lon``).
    excluded:
        Station IDs to skip (already tried).
    max_occupancy:
        Maximum vehicles charging before the station is considered full.
    """
    best: Optional[Tuple[float, str]] = None

    for station_id, station in stations.items():
        if station_id in excluded:
            continue
        if not station.get("operational", True):
            continue
        if len(station.get("vehicles_charging", [])) >= max_occupancy:
            continue

        info = ev_stations_info.get(station_id)
        if info is None:
            continue

        dist = haversine_distance(
            vehicle_lat, vehicle_lon, info["lat"], info["lon"],
        )
        if best is None or dist < best[0]:
            best = (dist, station_id)

    return best[1] if best else None
