"""Tests for v2g.core data types."""

from datetime import datetime

from v2g.core import V2GContract, V2GSession


def test_v2g_contract_defaults():
    c = V2GContract(
        vehicle_id="ev_1",
        substation_id="Times Square",
        power_provided_kw=50.0,
        start_time=datetime(2025, 1, 1),
        duration_seconds=3600,
        price_per_kwh=0.15,
    )
    assert c.total_earnings == 0.0
    assert c.status == "active"


def test_v2g_session_defaults():
    s = V2GSession(
        session_id="sess_1",
        vehicle_id="ev_2",
        station_id="st_1",
        substation_id="Penn Station",
        initial_soc=0.8,
        current_soc=0.6,
    )
    assert s.power_delivered_kwh == 0.0
    assert s.earnings == 0.0
    assert s.locked_at_station is True
    assert s.end_time is None
