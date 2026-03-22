"""
Intent detection helpers for chatbot messages.

These are consumed by ``ultra_intelligent_chatbot`` and can be extended
independently of the chatbot implementations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_GRID_KEYWORDS = re.compile(
    r"\b(grid|power|substation|voltage|load|outage|blackout|failure|restore)\b", re.I,
)
_TRAFFIC_KEYWORDS = re.compile(
    r"\b(traffic|vehicle|sumo|spawn|car|ev|charging|station|route)\b", re.I,
)
_V2G_KEYWORDS = re.compile(
    r"\b(v2g|discharge|contract|revenue|session|energy trading)\b", re.I,
)
_SCENARIO_KEYWORDS = re.compile(
    r"\b(scenario|time|temperature|weather|rush.?hour|midday|night)\b", re.I,
)


@dataclass
class Intent:
    """Detected intent with an optional confidence score."""

    name: str
    confidence: float = 1.0
    entity: Optional[str] = None


def classify(message: str) -> Intent:
    """Classify a user message into a coarse intent category."""
    msg = message.strip()
    if _V2G_KEYWORDS.search(msg):
        return Intent("v2g")
    if _GRID_KEYWORDS.search(msg):
        return Intent("grid")
    if _TRAFFIC_KEYWORDS.search(msg):
        return Intent("traffic")
    if _SCENARIO_KEYWORDS.search(msg):
        return Intent("scenario")
    return Intent("general")
