# SumoXPypsa

Manhattan co-simulation that couples:

- **Power grid**: PyPSA-based distribution model (substations, loads, cables)
- **Traffic**: SUMO (TraCI/libsumo) vehicle simulation
- **EV charging + V2G**: charging stations, session management, revenue model
- **Web dashboard**: Flask + Socket.IO + Mapbox visualization

## Quickstart

### 1) Enter the container and start the app

From the repo root:

```bash
bash run.sh
```

This script expects to run inside the project's distrobox container (it will tell you what to do if you're not).

If you need to set up from scratch:

```bash
distrobox enter sumoxpypsa
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set your OPENAI_API_KEY in .env for AI chatbot features
bash run.sh
```

### 2) Open the dashboard

- App: `http://localhost:5000`
- Perf snapshot: `http://localhost:5000/api/perf`
- Scenario files: `http://localhost:5000/api/scenario/files`

## Architecture (high-level)

```
main_complete_integration.py   ← Flask app (thin wrapper)
├── simulation/loop.py         ← Background sim thread (timing, perf stats)
├── simulation/context.py      ← SimulationContext dataclass, shared state
├── integrated_backend.py      ← ManhattanIntegratedSystem (canonical orchestrator)
├── sumo_mgr/                  ← SUMO management package (named to avoid shadowing eclipse-sumo)
│   ├── manager.py             ← SumoManagerProtocol + façade class
│   ├── spawn.py               ← Vehicle spawning helpers
│   ├── charging.py            ← Station selection / charging power helpers
│   └── traffic_lights.py      ← Signal-state builder functions
├── v2g/                       ← V2G package
│   └── core.py                ← V2GContract / V2GSession dataclasses
├── chatbot/                   ← Chatbot package
│   ├── base.py                ← Chatbot Protocol
│   ├── factory.py             ← select_chatbot() priority chain
│   ├── intents.py             ← Intent classification helpers
│   └── context.py             ← Per-user conversation store
├── config/
│   ├── settings.py            ← Pydantic-based settings
│   ├── ev_bus_mapping.py      ← Substation → PyPSA bus name map
│   └── logging.py             ← structlog configuration
├── scenarios/                 ← Declarative JSON scenario files
├── app/
│   ├── perf_routes.py         ← /api/perf endpoint
│   └── __init__.py            ← register_app_routes()
└── core/
    ├── backends.py            ← PowerBackend / TrafficBackend Protocols
    ├── power_system.py        ← ManhattanPowerGrid (PyPSA wrapper)
    └── ...                    ← Legacy integration layers (compat only)
```

### Major components and how they interact

1. **Flask app** (`main_complete_integration.py`) initialises all systems, registers routes, and starts the simulation thread via `simulation.loop.start_simulation_thread()`.
2. **Simulation loop** (`simulation/loop.py`) runs in a daemon thread. Each tick it:
   - Advances SUMO by one step
   - Updates traffic light states via the integrated backend
   - Processes the vehicle spawn queue
   - Updates V2G sessions and EV load on the PyPSA network
   - Runs DC power flow and collects performance metrics
3. **SUMO manager** (`sumo_mgr/manager.py`) wraps the base `ManhattanSUMOManager`, delegating traffic-light, spawn, and charging helpers to extracted submodules for testability.
4. **Chatbot factory** (`chatbot/factory.select_chatbot`) selects the best available chatbot (agentic → ultra → simple) and exposes a uniform `Chatbot` protocol to the API.
5. **Scenario controller** (`scenario_controller.py`) manages time-of-day, temperature, and substation monitoring. Declarative scenarios can be loaded from JSON files in `scenarios/`.

## Declarative Scenarios

Place JSON files in `scenarios/`. Example:

```json
{
  "name": "Evening Rush Hour",
  "time_of_day": 17.0,
  "temperature_c": 32,
  "ev_spawn_count": 50,
  "ev_percentage": 0.45,
  "battery_soc_range": [0.15, 0.7],
  "v2g_enabled": true,
  "forced_failures": []
}
```

Load via API: `POST /api/scenario/load_file` with `{"file": "rush_hour.json"}`.

## Testing

```bash
source venv/bin/activate
pytest -v
```

Test coverage includes: V2G core types, chatbot factory selection, EV bus mapping, SUMO helpers (traffic lights, spawn, charging), intent classification, and scenario file loading.

## Performance tips

- **libsumo vs TraCI**: The app auto-detects `libsumo` (in-process, ~10× faster). Falls back to socket-based `traci` if unavailable.
- **Step coarsening**: EV load and power flow updates run every 5 s of sim-time, not every 0.1 s tick.
- **Broadcast frame-skipping**: Socket.IO state broadcasts happen every 5 SUMO steps to reduce network overhead.
- **ML engine gating**: Online learning frequency and toggle are configurable via `config/settings.py` → `ml_config`.
- **Performance endpoint**: `GET /api/perf` returns average step times for SUMO, power flow, and total loop.

## Known limitations

- `manhattan_sumo_manager.py` is still a large monolithic file; the `sumo_mgr/` package provides a façade and extracted helpers but the base class has not been fully decomposed.
- `ultra_intelligent_chatbot.py` is monolithic; `chatbot/intents.py` and `chatbot/context.py` exist as extraction targets but the full refactor is incremental.
- No CI pipeline yet — tests are run locally. A Dockerfile and GitHub Actions workflow are planned.

## Docs

See the `docs/` directory for the roadmap status and additional notes.
