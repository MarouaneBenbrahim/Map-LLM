from __future__ import annotations

from flask import Flask, jsonify

from simulation.loop import get_perf_snapshot


def register_perf_routes(app: Flask) -> None:
    """Attach lightweight performance/metrics routes to the Flask app."""

    @app.route("/api/perf", methods=["GET"])
    def get_perf() -> tuple[dict, int]:
        """Return recent simulation-loop performance statistics as JSON."""
        return jsonify(get_perf_snapshot()), 200

