"""
Traffic light signal-state helpers.

Pure functions extracted from ``manhattan_sumo_manager.ManhattanSUMOManager``
so they can be tested independently and reused by the ``sumo.manager`` façade.
"""

from __future__ import annotations


def build_signal_state(phase: str, state_length: int) -> str:
    """Return a SUMO signal-state string for the given *phase* and link count.

    *phase* should be one of ``"green"``, ``"yellow"``, or ``"red"``
    (anything else is treated as red).
    """
    half = state_length // 2
    remainder = state_length - half

    if phase == "green":
        if state_length == 4:
            return "GGrr"
        if state_length == 8:
            return "GGGGrrrr"
        return "G" * half + "r" * remainder

    if phase == "yellow":
        if state_length == 4:
            return "yyrr"
        if state_length == 8:
            return "yyyyrrrr"
        return "y" * half + "r" * remainder

    # red (default)
    if state_length == 4:
        return "rrGG"
    if state_length == 8:
        return "rrrrGGGG"
    return "r" * half + "G" * remainder


def build_off_state(state_length: int) -> str:
    """Signal state when the traffic light has lost power (uncontrolled)."""
    return "o" * state_length


def build_blackout_state(state_length: int) -> str:
    """Signal state during a blackout (flashing yellow / caution)."""
    return "y" * state_length


def build_all_red_state(state_length: int) -> str:
    """Force every link to red (testing / emergency)."""
    return "r" * state_length
