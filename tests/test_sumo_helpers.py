"""Tests for the extracted sumo/ helper modules."""

from sumo_mgr.traffic_lights import (
    build_signal_state,
    build_off_state,
    build_blackout_state,
    build_all_red_state,
)
from sumo_mgr.spawn import (
    determine_vehicle_type,
    compute_initial_soc,
    compute_vehicle_color,
    compute_battery_capacity,
)
from sumo_mgr.charging import select_charging_power_kw, haversine_distance, find_nearest_station


# --- traffic_lights ---

def test_green_4():
    assert build_signal_state("green", 4) == "GGrr"


def test_green_8():
    assert build_signal_state("green", 8) == "GGGGrrrr"


def test_red_4():
    assert build_signal_state("red", 4) == "rrGG"


def test_yellow_8():
    assert build_signal_state("yellow", 8) == "yyyyrrrr"


def test_off_state():
    assert build_off_state(6) == "oooooo"


def test_blackout_state():
    assert build_blackout_state(4) == "yyyy"


def test_all_red():
    assert build_all_red_state(8) == "rrrrrrrr"


# --- spawn ---

def test_determine_vehicle_type_returns_tuple():
    vtype, is_ev = determine_vehicle_type(ev_percentage=1.0)
    assert is_ev is True
    assert vtype in ("ev_sedan", "ev_suv")


def test_determine_vehicle_type_ice():
    vtype, is_ev = determine_vehicle_type(ev_percentage=0.0)
    assert is_ev is False
    assert vtype in ("car", "taxi")


def test_compute_initial_soc_range():
    soc = compute_initial_soc(0.2, 0.8)
    assert 0.2 <= soc <= 0.8


def test_compute_vehicle_color_ev_low():
    assert compute_vehicle_color(True, 0.1) == (255, 0, 0, 255)


def test_compute_vehicle_color_ev_ok():
    assert compute_vehicle_color(True, 0.5) == (0, 255, 0, 255)


def test_compute_vehicle_color_ice():
    assert compute_vehicle_color(False, 1.0) == (255, 255, 0, 255)


def test_battery_capacity():
    assert compute_battery_capacity("ev_sedan") == 75_000
    assert compute_battery_capacity("ev_suv") == 100_000
    assert compute_battery_capacity("car") == 0


# --- charging ---

def test_charging_power_tiers():
    assert select_charging_power_kw(0) == 0
    assert select_charging_power_kw(3) == 150
    assert select_charging_power_kw(7) == 100
    assert select_charging_power_kw(12) == 50
    assert select_charging_power_kw(20) == 22


def test_haversine_same_point():
    assert haversine_distance(40.75, -73.99, 40.75, -73.99) == 0.0


def test_haversine_positive_distance():
    d = haversine_distance(40.75, -73.99, 40.76, -73.98)
    assert d > 0


def test_find_nearest_station_basic():
    stations = {
        "st1": {"operational": True, "vehicles_charging": []},
        "st2": {"operational": True, "vehicles_charging": ["v1", "v2"]},
    }
    info = {
        "st1": {"lat": 40.76, "lon": -73.99},
        "st2": {"lat": 40.75, "lon": -73.98},
    }
    result = find_nearest_station(40.755, -73.985, stations, info, excluded=[])
    assert result in ("st1", "st2")


def test_find_nearest_station_excludes():
    stations = {
        "st1": {"operational": True, "vehicles_charging": []},
    }
    info = {
        "st1": {"lat": 40.76, "lon": -73.99},
    }
    result = find_nearest_station(40.755, -73.985, stations, info, excluded=["st1"])
    assert result is None
