"""
EV-station ↔ PyPSA bus name mapping.

Centralises the mapping so it is not hardcoded inside the simulation loop.
"""

from __future__ import annotations

from typing import Dict

EV_BUS_MAPPING: Dict[str, str] = {
    "Hell's Kitchen": "Hell's Kitchen_13.8kV",
    "Times Square": "Times Square_13.8kV",
    "Penn Station": "Penn Station_13.8kV",
    "Grand Central": "Grand Central_13.8kV",
    "Murray Hill": "Murray Hill_13.8kV",
    "Turtle Bay": "Turtle Bay_13.8kV",
    "Columbus Circle": "Chelsea_13.8kV",
    "Midtown East": "Midtown East_13.8kV",
}
