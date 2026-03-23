# Agent Refactoring Instructions for SumoXPypsa

## Project Context
SumoXPypsa is a co-simulation application bridging a PyPSA modeled electrical distribution grid in Manhattan with urban traffic simulated via SUMO. It includes EV charging, V2G (vehicle-to-grid) logic, and an integrated web dashboard built with Flask and Flask-SocketIO. 

The simulation loop runs in a background thread (`simulation/loop.py`) while the web server handles HTTP/WebSocket APIs. 

## Coding Standards & Tooling
When generating code or refactoring existing files, you MUST adhere to the following standards:
* **Language:** Python 3.12.
* **Formatting:** Black and Ruff are configured via `pyproject.toml`.
* **Line Length:** Strictly 100 characters.
* **Testing:** Pytest. Ensure all refactored logic maintains or increases test coverage.
* **No Emojis:** Do not include any emojis in comments, docstrings, or print statements.
* **Punctuation:** Do not use em dashes in documentation or comments. Use standard hyphens, colons, or parentheses instead.

## Architectural Source of Truth & Deprecation Rules
The codebase contains legacy duplication that needs to be phased out. When modifying integration logic, follow these routing rules:

1. **The Integrated System:**
   * **Canonical:** `/integrated_backend.py` (root level). This contains the `ManhattanIntegratedSystem`.
   * **Legacy to Deprecate:** `/core/integrated_backend.py` and alternate paths like `/core/world_class_system.py`. Move references to the root version and remove legacy files when isolated.

2. **SUMO Management:**
   * **Canonical/Target State:** The `/sumo_mgr/` directory (contains `SumoManagerProtocol`, `traffic_lights.py`, `spawn.py`, etc.) and `/core/sumo_manager.py` (the app's subclass).
   * **Legacy to Deprecate:** `/manhattan_sumo_manager.py`. Refactor dependencies away from this massive legacy class and into the modularized `sumo_mgr/` helpers.

3. **V2G Types:**
   * **Canonical:** `/v2g/core.py` (contains `V2GContract`, `V2GSession`).
   * **Legacy/Demo:** `/enhanced_v2g_manager.py` is marked as a demo. Do not route core logic here. Use `/v2g_manager.py`.

## Core Refactoring Directives

### 1. Separation of Concerns (Thread Safety)
The simulation loop (`simulation/loop.py`) operates in a background thread on a specific cadence. 
* Never introduce synchronous blocking calls to the Flask web routes that rely on the simulation thread.
* State sharing between the Flask app (`main_complete_integration.py`) and the simulation loop must go through safe global contexts like `simulation/context.py` or defined queues.

### 2. Route Abstraction
`main_complete_integration.py` is currently a monolith that registers many routes and initializes all engines. 
* **Goal:** Extract route definitions into modular blueprints (e.g., moving performance routes to `app/perf_routes.py` and scenario routes to `scenario_integration.py`). 
* Keep `main_complete_integration.py` strictly for dependency injection, app factory creation, and starting the background thread.

### 3. AI and Chatbot Unification
There are multiple chatbot implementations (`ai_chatbot.py`, `ultra_intelligent_chatbot.py`, `agentic_chatbot.py`). 
* **Goal:** Ensure all chat endpoints route through the unified `/api/ai/chat` path.
* Utilize `chatbot/factory.py` (`select_chatbot()`) to manage instantiation rather than hardcoding specific bot classes in the main integration file.

### 4. Scenario Management
Scenarios are declarative JSON files in `/scenarios/`. 
* Ensure `scenario_controller.py` and `scenario_integration.py` act as the sole bridge between these JSON files and the `ManhattanIntegratedSystem`. 
* Remove any hardcoded simulation states in the initialization phases that bypass the scenario loader.

## Execution Protocol for the Agent
1. **Analyze First:** Before modifying a file, read the canonical version and the legacy version to ensure no custom logic is lost during deduplication.
2. **Atomic Changes:** Refactor one module at a time (e.g., fix SUMO imports before touching PyPSA power flow).
3. **Verify Imports:** Whenever a legacy file is targeted for deprecation, globally search for its imports and repoint them to the canonical equivalent.
4. **Run Tests:** Assume a continuous integration mindset. Write Pytest fixtures for any newly abstracted modular classes (especially in `sumo_mgr/` and `chatbot/`).