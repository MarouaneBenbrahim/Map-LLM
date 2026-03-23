"""
SUMO manager façade and stable interface.

``SumoManagerProtocol`` defines the contract consumed by the simulation loop.
``ManhattanSUMOManager`` is the concrete implementation—it extends the
monolithic base class and progressively delegates to the extracted submodules
(``sumo.traffic_lights``, ``sumo.spawn``, ``sumo.charging``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from manhattan_sumo_manager import ManhattanSUMOManager as _BaseSUMOManager

from . import traffic_lights as tl_helpers
from . import spawn as spawn_helpers
from . import charging as charging_helpers


@runtime_checkable
class SumoManagerProtocol(Protocol):
    """Stable interface the simulation loop relies on."""

    running: bool
    vehicles: Dict[str, Any]

    def start(self, scenario: Any = None) -> bool: ...

    def stop(self) -> None: ...

    def step(self) -> None: ...

    def spawn_vehicles(
        self,
        count: int = 10,
        ev_percentage: float = 0.3,
        battery_min_soc: float = 0.2,
        battery_max_soc: float = 0.9,
    ) -> int: ...

    def update_traffic_lights(self) -> None: ...

    def handle_blackout_traffic_lights(self, affected_substations: Any) -> None: ...

    def get_statistics(self) -> Dict[str, Any]: ...


class ManhattanSUMOManager(_BaseSUMOManager):
    """Project-stable SUMO manager entrypoint.

    Overrides selected base-class methods to delegate to the extracted
    helper modules, keeping ``manhattan_sumo_manager.py`` untouched for
    backward compatibility.
    """

    # -- traffic-light helpers delegated to sumo.traffic_lights ----------

    def _build_signal_state(self, phase: str, state_length: int) -> str:
        return tl_helpers.build_signal_state(phase, state_length)

    def _build_off_state(self, state_length: int) -> str:
        return tl_helpers.build_off_state(state_length)

    def _build_blackout_state(self, state_length: int) -> str:
        return tl_helpers.build_blackout_state(state_length)

    def _build_all_red_state(self, state_length: int) -> str:
        return tl_helpers.build_all_red_state(state_length)

    # -- spawn helpers delegated to sumo.spawn ---------------------------

    @staticmethod
    def _determine_vehicle_type(ev_percentage: float = 0.3):
        return spawn_helpers.determine_vehicle_type(ev_percentage)

    @staticmethod
    def _compute_vehicle_color(is_ev: bool, initial_soc: float):
        return spawn_helpers.compute_vehicle_color(is_ev, initial_soc)

    @staticmethod
    def _compute_battery_capacity(vtype: str) -> int:
        return spawn_helpers.compute_battery_capacity(vtype)

    # -- charging helpers delegated to sumo.charging ---------------------

    def _find_available_charging_station(
        self, vehicle_id: str, excluded_stations: list,
    ) -> Optional[str]:
        """Override to use extracted ``find_nearest_station`` logic."""
        if not self.station_manager:
            return None

        try:
            from sumo_mgr.traci_compat import traci

            x, y = traci.vehicle.getPosition(vehicle_id)
            vehicle_lon, vehicle_lat = traci.simulation.convertGeo(x, y)
        except Exception:
            return None

        return charging_helpers.find_nearest_station(
            vehicle_lat,
            vehicle_lon,
            self.station_manager.stations,
            self.integrated_system.ev_stations,
            excluded_stations,
        )
