"""Tests for chatbot.intents intent classification."""

from chatbot.intents import classify


def test_grid_intent():
    assert classify("What is the grid voltage?").name == "grid"


def test_traffic_intent():
    assert classify("How many vehicles are spawned?").name == "traffic"


def test_v2g_intent():
    assert classify("Show V2G revenue from contracts").name == "v2g"


def test_scenario_intent():
    assert classify("Change to rush hour scenario").name == "scenario"


def test_general_intent():
    assert classify("Hello, how are you?").name == "general"
