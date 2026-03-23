## SumoXPypsa Roadmap Status

This document tracks the implementation status of the improvement roadmap.

---

### 1. Architectural Refactors

- **extract-simulation-core**: **completed**
  Simulation loop and shared state extracted into `simulation/loop.py` and `simulation/context.py`. `main_complete_integration.py` delegates to `start_simulation_thread()` and `create_simulation_context()`. A `SimulationContext` dataclass passes dependencies explicitly.

- **unify-integration-layer**: **completed**
  `ManhattanIntegratedSystem` in `integrated_backend.py` is the canonical integration orchestrator. `core/backends.py` defines `PowerBackend` and `TrafficBackend` Protocols. Legacy backends under `core/` remain only for compatibility.

- **modularize-sumo**: **completed**
  - `sumo_mgr/manager.py` defines `SumoManagerProtocol` (lifecycle + step + spawn + traffic-light contract) and a `ManhattanSUMOManager` façade that delegates to extracted helpers.
  - `sumo_mgr/traffic_lights.py` — pure functions: `build_signal_state()`, `build_off_state()`, `build_blackout_state()`, `build_all_red_state()`.
  - `sumo_mgr/spawn.py` — `determine_vehicle_type()`, `compute_initial_soc()`, `compute_vehicle_color()`, `compute_battery_capacity()`.
  - `sumo_mgr/charging.py` — `select_charging_power_kw()`, `haversine_distance()`, `find_nearest_station()`.
  - `sumo_mgr/types.py` re-exports `VehicleType`, `SimulationScenario`, `VehicleConfig`, `Vehicle`.
  - `sumo_mgr/__init__.py` exports all public names including `SumoManagerProtocol`.

- **consolidate-v2g**: **completed**
  `V2GManager` in `v2g_manager.py` is the single system-wide implementation. Shared data types (`V2GContract`, `V2GSession`) live in `v2g/core.py`. `enhanced_v2g_manager.py` is demo-only.

- **cleanup-chatbot-architecture**: **completed**
  - `chatbot/base.py` defines the `Chatbot` Protocol (`is_available()`, `async chat()`).
  - `chatbot/factory.py` provides `select_chatbot()` with adapters for sync and async bots, plus an `_UnavailableChatbot` fallback.
  - `chatbot/intents.py` — keyword-based intent classifier (`classify()` → grid / traffic / v2g / scenario / general).
  - `chatbot/context.py` — `ConversationStore` with per-user turn history.
  - `main_complete_integration.py` now imports `select_chatbot`, builds `active_chatbot` after initialization, and the `/api/ai/chat` endpoint uses it instead of the manual fallback chain.

### 2. Performance & Scalability

- **optimize-performance-hotspots**: **completed**
  - Simulation loop (`simulation/loop.py`) records per-section timing (`sumo_step`, `ev_update`, `power_flow`, `total_step`) and updates `_PERF_LATEST` every 30 sim-seconds.
  - `app/perf_routes.py` exposes `GET /api/perf` returning JSON performance stats.
  - EV-bus mapping extracted to `config/ev_bus_mapping.py` (was hardcoded in loop).
  - EV load updates run every 5 s sim-time (not every 0.1 s tick).
  - Power flow runs every 5 s sim-time.
  - V2G sessions update every 1 s sim-time.
  - Socket.IO broadcast frame-skipping (every 5 SUMO steps).
  - ML engine `online_learning_enabled` and `model_update_frequency` are configurable via `config/settings.py` → `ml_config`.

### 3. Code Quality, Testing, and Tooling

- **expand-tests-and-toolkits**: **completed**
  - `pyproject.toml` configured with `ruff` (select E/F/I/B/UP) and `black` (line-length 100, py312).
  - `torch` import guarded with try/except in `config/settings.py`.
  - New test files:
    - `tests/test_v2g_core.py` — V2GContract and V2GSession defaults.
    - `tests/test_chatbot_factory.py` — select_chatbot priority, adapters, unavailable handling.
    - `tests/test_chatbot_intents.py` — intent classification (grid, traffic, v2g, scenario, general).
    - `tests/test_ev_bus_mapping.py` — mapping validity and known substations.
    - `tests/test_sumo_helpers.py` — traffic light states, spawn helpers, charging power tiers, haversine, station finder.
    - `tests/test_scenario_loader.py` — list_scenario_files, missing-dir handling.
  - Existing: `tests/test_settings.py` — settings import and torch guard.

### 4. Documentation, Scenarios, and UI

- **improve-docs-and-ui**: **completed**
  - `README.md` rewritten with: high-level overview, quickstart, full architecture tree, component interaction explanation, declarative scenarios section, testing section, performance tips, and known limitations.
  - `scenarios/` directory created with 4 JSON scenario files:
    - `midday.json` — normal midday operations
    - `rush_hour.json` — evening rush hour stress
    - `blackout_test.json` — forced substation failures
    - `night_low_load.json` — overnight low-load
  - `scenario_controller.py` gained `load_scenario_file(path)` and `list_scenario_files(directory)` methods.
  - `scenario_integration.py` gained `GET /api/scenario/files` and `POST /api/scenario/load_file` endpoints.
  - `docs/roadmap-status.md` (this file) updated to reflect final status.

### 5. Longer-Term Refactors (Optional — not in current scope)

- **Plugin system for backends and tools**: not started.
- **Typed interfaces and gradual typing**: partial — Protocols defined for PowerBackend, TrafficBackend, SumoManagerProtocol, Chatbot; full mypy configuration not yet added.
- **Containerization and CI**: not started — Dockerfile and GitHub Actions workflow are planned.
