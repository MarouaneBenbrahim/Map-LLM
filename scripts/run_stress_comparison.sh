#!/usr/bin/env bash
# Run stress benchmark twice: libsumo (default) vs socket traci (pre-libsumo style).
# Usage (from repo root, inside venv or with PYTHONPATH set):
#   ./scripts/run_stress_comparison.sh
# Optional env:
#   BENCH_PYTHON=venv/bin/python
#   BENCH_VEHICLES=1000 BENCH_WARMUP=120 BENCH_MEASURE=400

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${BENCH_PYTHON:-${ROOT}/venv/bin/python}"
VEH="${BENCH_VEHICLES:-1000}"
WU="${BENCH_WARMUP:-120}"
MS="${BENCH_MEASURE:-400}"

if [[ ! -x "$PY" && "$PY" != *python* ]]; then
  echo "Python not found at $PY — set BENCH_PYTHON or create venv at ${ROOT}/venv"
  exit 1
fi

COMMON=(scripts/stress_perf_benchmark.py --vehicles "$VEH" --warmup "$WU" --measure "$MS")

echo "=== Stress benchmark: libsumo (in-process) ==="
"$PY" "${COMMON[@]}"

echo ""
echo "=== Stress benchmark: socket traci (FORCE_TRACI / pre-libsumo style) ==="
"$PY" "${COMMON[@]}" --force-traci

echo ""
echo "=== Summary (mean SUMO step ms) ==="
export ROOT
"$PY" - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["ROOT"])
for name, path in [
    ("libsumo", root / "stress_benchmark_libsumo.json"),
    ("socket_traci", root / "stress_benchmark_socket_traci.json"),
]:
    p = Path(path)
    if not p.exists():
        print(f"{name}: (missing {p})")
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    sm = d.get("sumo_step_ms", {})
    print(
        f"{name}: mean={sm.get('mean')} ms  p95={sm.get('p95')} ms  "
        f"wall={d.get('wall_clock_s')} s"
    )
PY
