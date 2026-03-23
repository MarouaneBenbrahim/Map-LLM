#!/usr/bin/env python3
"""
Stress-test performance: libsumo vs socket traci (approximates pre-libsumo runs).

Usage (from repo root, with venv):

  # libsumo (default)
  python scripts/stress_perf_benchmark.py --vehicles 1000 --warmup 120 --measure 400

  # Socket traci (same as FORCE_TRACI=1)
  python scripts/stress_perf_benchmark.py --force-traci --vehicles 1000 --warmup 120 --measure 400

Set FORCE_TRACI before importing the project is not required; use --force-traci instead.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

# Repo root on sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _apply_force_traci_flag(force_traci: bool) -> None:
    if force_traci:
        os.environ["FORCE_TRACI"] = "1"
    else:
        os.environ.pop("FORCE_TRACI", None)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stress perf: SUMO step times (libsumo vs traci)")
    parser.add_argument("--force-traci", action="store_true", help="Use socket traci (pre-libsumo style)")
    parser.add_argument("--vehicles", type=int, default=1000, help="Vehicles to spawn (stress test)")
    parser.add_argument("--ev-fraction", type=float, default=0.6, help="EV fraction (0..1)")
    parser.add_argument("--warmup", type=int, default=120, help="Warmup steps before timing")
    parser.add_argument("--measure", type=int, default=400, help="Timed steps")
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write results JSON (default: stress_benchmark_<mode>.json)",
    )
    args = parser.parse_args()

    force_traci = args.force_traci
    _apply_force_traci_flag(force_traci)

    # Load traci_compat before core.sumo_manager (otherwise manhattan_sumo_manager imports it first).
    import sumo_mgr.traci_compat as tc  # noqa: WPS433

    from core.power_system import ManhattanPowerGrid  # noqa: WPS433
    from integrated_backend import ManhattanIntegratedSystem  # noqa: WPS433
    from core.sumo_manager import ManhattanSUMOManager  # noqa: WPS433

    mode = "socket_traci" if force_traci else "libsumo"
    print(f"[bench] mode={mode} USING_LIBSUMO={tc.USING_LIBSUMO} FORCE_TRACI={tc.FORCE_TRACI}")

    if not tc.SUMO_AVAILABLE:
        print("[bench] ERROR: SUMO bindings not available (install traci/libsumo).", file=sys.stderr)
        return 1

    print("[bench] Initializing power grid + integrated system (one-time cost)...")
    power_grid = ManhattanPowerGrid()
    integrated_system = ManhattanIntegratedSystem(power_grid)
    sumo_manager = ManhattanSUMOManager(integrated_system)

    print("[bench] Starting SUMO (headless)...")
    if not sumo_manager.start_sumo(gui=False):
        print("[bench] ERROR: start_sumo failed.", file=sys.stderr)
        return 1

    print(f"[bench] Spawning {args.vehicles} vehicles (ev_fraction={args.ev_fraction})...")
    spawned = sumo_manager.spawn_vehicles(
        args.vehicles,
        ev_percentage=args.ev_fraction,
    )
    print(f"[bench] Spawned {spawned} vehicles.")

    print(f"[bench] Warmup {args.warmup} steps...")
    for _ in range(args.warmup):
        sumo_manager.step()

    print(f"[bench] Measuring {args.measure} steps...")
    times_ms: list[float] = []
    t0 = time.perf_counter()
    for _ in range(args.measure):
        s = time.perf_counter()
        sumo_manager.step()
        times_ms.append((time.perf_counter() - s) * 1000.0)
    wall_s = time.perf_counter() - t0

    avg = statistics.mean(times_ms)
    p95 = _percentile(times_ms, 95)
    p99 = _percentile(times_ms, 99)
    med = statistics.median(times_ms)

    out = {
        "mode": mode,
        "using_libsumo": bool(tc.USING_LIBSUMO),
        "force_traci": bool(tc.FORCE_TRACI),
        "vehicles_requested": args.vehicles,
        "vehicles_spawned": spawned,
        "ev_fraction": args.ev_fraction,
        "warmup_steps": args.warmup,
        "measure_steps": args.measure,
        "wall_clock_s": round(wall_s, 3),
        "sumo_step_ms": {
            "mean": round(avg, 3),
            "median": round(med, 3),
            "p95": round(p95, 3),
            "p99": round(p99, 3),
            "min": round(min(times_ms), 3),
            "max": round(max(times_ms), 3),
        },
    }

    print(json.dumps(out, indent=2))
    print(
        f"[bench] mean={avg:.2f}ms  median={med:.2f}ms  p95={p95:.2f}ms  "
        f"wall={wall_s:.1f}s for {args.measure} steps"
    )

    out_path = args.json_out
    if out_path is None:
        out_path = Path(__file__).resolve().parents[1] / f"stress_benchmark_{mode}.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"[bench] Wrote {out_path}")

    try:
        sumo_manager.stop()
    except Exception:
        pass

    return 0


def _percentile(data: list[float], pct: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (k - f) * (s[c] - s[f])


if __name__ == "__main__":
    raise SystemExit(main())
