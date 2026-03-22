"""Tests for config.ev_bus_mapping."""

from config.ev_bus_mapping import EV_BUS_MAPPING


def test_mapping_is_not_empty():
    assert len(EV_BUS_MAPPING) > 0


def test_all_values_end_with_voltage():
    for name, bus in EV_BUS_MAPPING.items():
        assert bus.endswith("kV"), f"{name} -> {bus} does not end with kV"


def test_known_substations_present():
    expected = ["Times Square", "Penn Station", "Grand Central"]
    for sub in expected:
        assert sub in EV_BUS_MAPPING, f"{sub} not in EV_BUS_MAPPING"
