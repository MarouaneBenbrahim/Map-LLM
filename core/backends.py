"""
Backend interfaces for traffic/power integration.

`ManhattanIntegratedSystem` in `integrated_backend.py` is the canonical
implementation for the current app and is expected to satisfy these
protocols. Other, older integration layers (such as
`core/world_class_system.py` and `core/integrated_backend.py`) are
considered legacy and should not be used for new code.
"""

from __future__ import annotations

from typing import Any, Dict, Protocol


class PowerBackend(Protocol):
    """Abstract interface for the power-side of the integrated system."""

    power_grid: Any
    substations: Dict[str, Any]
    ev_stations: Dict[str, Any]

    def simulate_substation_failure(self, substation_name: str) -> Dict[str, Any]: ...

    def restore_substation(self, substation_name: str) -> bool: ...

    def get_network_state(self) -> Dict[str, Any]: ...


class TrafficBackend(Protocol):
    """Abstract interface for the traffic/visualization side."""

    traffic_lights: Dict[str, Any]

    def update_traffic_light_phases(self) -> None: ...

