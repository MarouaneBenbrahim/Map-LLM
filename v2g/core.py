from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class V2GContract:
    """Smart contract for V2G energy trading."""

    vehicle_id: str
    substation_id: str
    power_provided_kw: float
    start_time: datetime
    duration_seconds: float
    price_per_kwh: float
    total_earnings: float = 0.0
    status: str = "active"  # active, completed, cancelled


@dataclass
class V2GSession:
    """Individual V2G discharge session with basic metrics."""

    session_id: str
    vehicle_id: str
    station_id: str
    substation_id: str
    initial_soc: float
    current_soc: float
    power_delivered_kwh: float = 0.0
    earnings: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    locked_at_station: bool = True
    min_energy_required: float = 0.0
    target_discharge_duration: float = 0.0
    actual_power_kw: float = 0.0
    peak_power_kw: float = 0.0

