"""SUMO manager package.

``traci_compat`` is imported eagerly so ``from sumo_mgr.traci_compat import …`` never
pulls in ``manhattan_sumo_manager`` (avoids circular imports).  Heavier symbols
(``ManhattanSUMOManager``, types) load on first access.
"""

from __future__ import annotations

from typing import Any

from .traci_compat import FORCE_TRACI, SUMO_AVAILABLE, USING_LIBSUMO, init, sumolib, traci

__all__ = [
    "FORCE_TRACI",
    "ManhattanSUMOManager",
    "SimulationScenario",
    "SumoManagerProtocol",
    "SUMO_AVAILABLE",
    "USING_LIBSUMO",
    "Vehicle",
    "VehicleConfig",
    "VehicleType",
    "init",
    "sumolib",
    "traci",
]


def __getattr__(name: str) -> Any:
    if name == "ManhattanSUMOManager":
        from .manager import ManhattanSUMOManager

        return ManhattanSUMOManager
    if name == "SumoManagerProtocol":
        from .manager import SumoManagerProtocol

        return SumoManagerProtocol
    if name in ("VehicleType", "SimulationScenario", "VehicleConfig", "Vehicle"):
        from . import types as _types

        return getattr(_types, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
