from __future__ import annotations

"""
Application-level helpers and blueprints.

Exposes ``register_app_routes`` which registers performance/metrics routes
and all extracted Blueprints on a Flask app instance.
"""

from flask import Flask

from .perf_routes import register_perf_routes
from .core_routes import bp as core_bp, init_core_routes
from .sumo_routes import bp as sumo_bp, init_sumo_routes
from .grid_routes import bp as grid_bp, init_grid_routes
from .v2g_routes import bp as v2g_bp, init_v2g_routes
from .ai_routes import bp as ai_bp, init_ai_routes


def register_app_routes(app: Flask) -> None:
    """Register all application routes/blueprints on the given Flask app."""
    register_perf_routes(app)


def register_blueprints(
    app: Flask,
    *,
    power_grid,
    integrated_system,
    sumo_manager,
    v2g_manager,
    ai_chatbot,
    active_chatbot,
    ultra_chatbot,
    system_state,
    vehicle_spawn_queue,
    scenario_controller,
    preload_edge_shapes,
    select_chatbot_fn,
) -> None:
    """Initialize and register all extracted Blueprints on *app*."""

    init_core_routes(
        power_grid=power_grid,
        integrated_system=integrated_system,
        sumo_manager=sumo_manager,
        v2g_manager=v2g_manager,
        system_state=system_state,
    )
    app.register_blueprint(core_bp)

    init_sumo_routes(
        sumo_manager=sumo_manager,
        system_state=system_state,
        vehicle_spawn_queue=vehicle_spawn_queue,
        preload_edge_shapes=preload_edge_shapes,
        scenario_controller=scenario_controller,
    )
    app.register_blueprint(sumo_bp)

    init_grid_routes(
        power_grid=power_grid,
        integrated_system=integrated_system,
        sumo_manager=sumo_manager,
        v2g_manager=v2g_manager,
        system_state=system_state,
        scenario_controller=scenario_controller,
    )
    app.register_blueprint(grid_bp)

    init_v2g_routes(
        integrated_system=integrated_system,
        sumo_manager=sumo_manager,
        v2g_manager=v2g_manager,
        system_state=system_state,
    )
    app.register_blueprint(v2g_bp)

    init_ai_routes(
        ai_chatbot=ai_chatbot,
        active_chatbot=active_chatbot,
        ultra_chatbot=ultra_chatbot,
        integrated_system=integrated_system,
        sumo_manager=sumo_manager,
        system_state=system_state,
        select_chatbot_fn=select_chatbot_fn,
    )
    app.register_blueprint(ai_bp)
