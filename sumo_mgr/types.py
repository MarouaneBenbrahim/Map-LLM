"""
SUMO domain types.

These are re-exported from `manhattan_sumo_manager.py` for compatibility,
but new code should import from `sumo.types`.
"""

from __future__ import annotations

from manhattan_sumo_manager import VehicleType, SimulationScenario, VehicleConfig, Vehicle

__all__ = ["VehicleType", "SimulationScenario", "VehicleConfig", "Vehicle"]

