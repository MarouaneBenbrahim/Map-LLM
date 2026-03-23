# Refactor Summary

This document describes the architectural refactoring applied to the
SumoXPypsa codebase, what changed in each phase, and how the changes
improve the project.

---

## Motivation

Before the refactor, `main_complete_integration.py` was a ~2 400-line
monolith that handled Flask app creation, system initialization, 40+
inline route definitions, a duplicate simulation loop, and scattered
helper functions. This made it difficult to test individual routes, trace
the startup sequence, or understand the concurrency boundary between
Flask and the simulation thread. The AI chat layer had multiple
independent entry paths with opaque fallback logic, and the grid's
initial loads were hardcoded values that bypassed the scenario system.

The refactor was guided by four directives from
`AGENT_REFACTOR_INSTRUCTIONS.md`:

1. **Separation of concerns / thread safety** — no synchronous blocking
   calls in Flask routes; explicit shared-state boundary.
2. **Route abstraction** — extract routes into modular Flask Blueprints.
3. **AI and chatbot unification** — single chat protocol and factory.
4. **Scenario management** — all load initialization flows through
   `ScenarioController`; no hardcoded simulation states.

---

## Phase 1 — Legacy Cleanup

### What changed

- Removed the **dead duplicate `simulation_loop()`** (lines 386–549 of
  the old main file) and its associated helpers (`update_ev_power_loads`,
  `check_n_minus_1_contingency`, etc.). The actual simulation loop lives
  in `simulation/loop.py` and was already running at runtime; the copy
  in main was never called.
- Fixed a missing `send_file` import in Flask that caused the
  `/api/export-state` route to crash with a `NameError`.

### Why it helps

Dead code actively misleads developers who read it assuming it runs. Its
removal makes the main file shorter and eliminates a source of
divergence (changes to `simulation/loop.py` would not have been
reflected in the dead copy).

---

## Phase 2 — Route Extraction into Blueprints

### What changed

All inline route definitions were moved out of
`main_complete_integration.py` into five new Blueprint modules:

| Module | Routes | Responsibility |
|--------|--------|----------------|
| `app/core_routes.py` | `GET /`, `/api/status`, `/api/config`, `/api/debug/*`, `/api/network_state`, `/api/export-state` | Dashboard serving, system status, debug introspection |
| `app/sumo_routes.py` | `/api/sumo/start`, `/api/sumo/stop`, `/api/sumo/spawn`, `/api/sumo/scenario`, `/api/ev/config`, `/api/simulation/speed` | SUMO lifecycle, vehicle spawning, EV configuration |
| `app/grid_routes.py` | `/api/fail/*`, `/api/restore/*`, `/api/snapshot/state`, `/api/report/generate`, `/api/restore_all` | Substation failure/restore, state snapshots, PDF reports |
| `app/v2g_routes.py` | `/api/v2g/enable/*`, `/api/v2g/disable/*`, `/api/v2g/status`, `/api/v2g/start_session`, `/api/v2g/test` | V2G session management |
| `app/ai_routes.py` | `/api/ai/chat`, `/api/ai/predict`, `/api/ai/report`, `/api/ai/v2g/optimize`, `/api/ai/enhanced/*`, `/api/map/focus` | AI chat, predictions, map focus |

Each blueprint receives its dependencies through an explicit
`init_*_routes()` function rather than closing over local variables in
main. The wiring happens in `app/__init__.py`'s `register_blueprints()`.

`main_complete_integration.py` was reduced to **355 lines** and now does
only three things:

1. Initialize domain objects (power grid, integrated system, SUMO
   manager, V2G manager, ML engine, chatbots, scenario controller).
2. Register all blueprints via `register_blueprints(app, ...)`.
3. Start the simulation thread and serve the app.

### Why it helps

- **Testability** — each blueprint can be mounted in an isolated Flask
  test client with mock dependencies, without booting the entire
  application.
- **Readability** — the main file reads as a linear initialization
  script; route logic lives next to related route logic rather than
  interleaved with unrelated endpoints.
- **Maintainability** — adding or modifying a V2G endpoint means editing
  `app/v2g_routes.py`, not scrolling through 2 400 lines to find the
  right section.

---

## Phase 3 — AI / Chatbot Unification

### What changed

- Removed the `advanced_ai_controller` import and `world_class_ai`
  fallback variable from main. This was a last-resort chat path that
  bypassed the `Chatbot` protocol entirely.
- All chat traffic now flows through a single path:
  `chatbot/factory.py`'s `select_chatbot()` evaluates available
  implementations at startup and wraps the best one in an adapter
  conforming to `chatbot/base.py`'s `Chatbot` protocol.

The priority order is:

1. **AgenticChatbot** — LLM agent with tool-calling (requires
   OpenAI-compatible endpoint).
2. **UltraIntelligentChatbot** — LLM-backed without tools.
3. **ManhattanAIChatbot** — rule-based, always available.

The protocol itself is minimal:

```python
class Chatbot(Protocol):
    def is_available(self) -> bool: ...
    async def chat(self, message: str, user_id: str = "web_user") -> Dict[str, Any]: ...
```

### Why it helps

- **Predictability** — `POST /api/ai/chat` always goes through the same
  code path regardless of which backend is active.
- **Extensibility** — adding a new chatbot implementation requires only
  implementing two methods and registering it in the factory; no route
  changes needed.
- **Cleanup** — `advanced_ai_controller.py` is now dead code (nothing
  imports it), making it safe to delete.

---

## Phase 4 — Scenario-Driven Initialization

### What changed

**4a — Default scenario file:**

The hardcoded `initial_loads` dictionary (lines 68–94 of the old main
file) was removed. In its place, a declarative JSON scenario file was
created at `scenarios/default.json`:

```json
{
  "name": "Default Startup",
  "description": "Default scenario loaded at application startup.",
  "time_of_day": 12.0,
  "temperature_c": 22,
  "ev_spawn_count": 0,
  "ev_percentage": 0.3,
  "battery_soc_range": [0.2, 0.9],
  "v2g_enabled": false,
  "forced_failures": []
}
```

This file is loaded at startup through the standard
`scenario_controller.load_scenario_file()` path, so the initial grid
state is computed by `RealisticLoadModel` — the same code that governs
runtime load changes.

**4b — SUMO ↔ ScenarioController synchronization:**

- `POST /api/sumo/start` now calls
  `scenario_controller.add_vehicles(count)` after spawning vehicles, so
  grid-side EV load counts stay in sync with the traffic side.
- `POST /api/sumo/scenario` (EV_RUSH preset) now calls
  `scenario_controller.run_scenario("rush_hour_stress_test")` so that
  the scenario controller's load model reflects the stress test
  conditions.

### Why it helps

- **Single source of truth** — load magnitudes are always computed by
  `RealisticLoadModel` based on time-of-day, temperature, and building
  types, whether at startup or during runtime.
- **Reproducibility** — the startup state is a JSON file that can be
  versioned, diffed, and swapped without code changes.
- **Consistency** — SUMO vehicle spawns are no longer invisible to the
  grid model; the scenario controller tracks EV counts and adjusts loads
  accordingly.

---

## Phase 5 — Test Coverage

### What changed

Two new test files were created:

- **`tests/test_route_blueprints.py`** — registers each blueprint in an
  isolated Flask test client with `MagicMock` dependencies. Verifies
  that key routes return expected HTTP status codes and JSON shapes
  without requiring SUMO, PyPSA, or any external service.

- **`tests/test_scenario_controller.py`** — covers the dynamic
  behaviors of `ScenarioController` (`set_time`, `run_scenario`,
  `load_scenario_file`) and verifies that `scenarios/default.json`
  exists and is structurally valid.

### Test results

All **66 tests pass**. One pre-existing failure in
`test_chatbot_intents.py::test_traffic_intent` was identified as
unrelated to the refactor (a classification edge case in the intent
parser).

---

## Before and After

| Metric | Before | After |
|--------|--------|-------|
| `main_complete_integration.py` line count | ~2 400 | 355 |
| Inline route definitions in main | ~40 | 0 |
| AI chat entry paths | 3+ with opaque fallbacks | 1 unified protocol |
| Initial grid load source | Hardcoded dictionary | `scenarios/default.json` via ScenarioController |
| SUMO ↔ grid EV load synchronization | None | `add_vehicles()` / `run_scenario()` callbacks |
| Route testability | Required full application boot | Blueprint + mock per route group |
| Dead code in main | Duplicate simulation loop + helpers | Removed |

---

## Files Created

| File | Purpose |
|------|---------|
| `app/__init__.py` | Blueprint registration orchestrator |
| `app/core_routes.py` | Core / status / debug routes |
| `app/sumo_routes.py` | SUMO / vehicle / simulation routes |
| `app/grid_routes.py` | Grid failure / restore / report routes |
| `app/v2g_routes.py` | V2G session routes |
| `app/ai_routes.py` | AI chat / prediction / map routes |
| `app/perf_routes.py` | Performance snapshot route |
| `scenarios/default.json` | Default startup scenario |
| `tests/test_route_blueprints.py` | Blueprint route tests |
| `tests/test_scenario_controller.py` | Scenario controller tests |

## Files Modified

| File | Change |
|------|--------|
| `main_complete_integration.py` | Stripped to init + blueprint registration + sim thread start |
| `app/sumo_routes.py` | Added ScenarioController callbacks on spawn/scenario |
| `chatbot/factory.py` | Unchanged (already existed); now the sole chat selection path |

## Files Made Obsolete

| File | Reason |
|------|--------|
| `advanced_ai_controller.py` | Nothing imports it after `world_class_ai` removal |
| `core/integrated_backend.py` | Superseded by root `integrated_backend.py` |
| `core/world_class_system.py` | Legacy integration layer; zero importers |
| `performance_metrics_generator.py` | `app/perf_routes.py` uses `simulation.loop.get_perf_snapshot()` instead |
| `core/traffic_system.py` | Zero importers; contains broken orphaned route snippets |
| `core/network_analyzer.py` | Zero importers |
| `config/logging.py` | Defines `setup_logging()` but nothing imports it |
