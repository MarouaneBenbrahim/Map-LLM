"""Single source of truth for the traci / libsumo API object.

Every module that needs ``traci`` should import it from here::

    from sumo_mgr.traci_compat import traci, sumolib

Call ``init()`` once at application startup (before the SUMO manager is
created) to select the backend.  By default libsumo is preferred for its
in-process performance advantage; set *force_traci* or the environment
variable ``FORCE_TRACI=1`` to fall back to the socket-based traci client
(required for ``sumo-gui``).
"""

from __future__ import annotations

import os
import types
from typing import Optional

SUMO_AVAILABLE: bool = False
USING_LIBSUMO: bool = False
FORCE_TRACI: bool = False

traci: Optional[types.ModuleType] = None  # type: ignore[assignment]
sumolib: Optional[types.ModuleType] = None  # type: ignore[assignment]

_INITIALIZED = False


def _deprioritize_sumo_tools_on_sys_path() -> None:
    """Put ``$SUMO_HOME/tools`` at the *end* of ``sys.path``.

    Startup scripts often prepend the distro SUMO ``tools`` directory to
    ``PYTHONPATH``.  Python inserts that block *before* ``site-packages``, so
    the system ``traci`` / ``sumolib`` packages shadow pip-installed bindings
    and prevent ``libsumo`` from loading correctly.  Moving those entries to
    the end lets the venv / ``uv`` packages win.
    """
    import sys

    sumo_home = os.environ.get("SUMO_HOME", "").strip()
    tools_norm: set[str] = set()
    if sumo_home:
        tools_norm.add(os.path.normpath(os.path.join(sumo_home, "tools")))
    for entry in list(sys.path):
        if not entry:
            continue
        n = os.path.normpath(entry)
        if n.endswith(f"{os.sep}sumo{os.sep}tools"):
            tools_norm.add(n)

    deferred: list[str] = []
    kept: list[str] = []
    for entry in sys.path:
        if not entry:
            kept.append(entry)
            continue
        if os.path.normpath(entry) in tools_norm:
            deferred.append(entry)
        else:
            kept.append(entry)
    if deferred:
        sys.path[:] = kept + deferred


def init(*, force_traci: bool = False) -> None:
    """Select the traci backend.  Safe to call more than once (no-op after first)."""
    global traci, sumolib, SUMO_AVAILABLE, USING_LIBSUMO, FORCE_TRACI, _INITIALIZED

    if _INITIALIZED:
        return

    _deprioritize_sumo_tools_on_sys_path()

    force_traci = force_traci or os.environ.get("FORCE_TRACI", "0") == "1"
    FORCE_TRACI = force_traci

    if not force_traci:
        try:
            import libsumo as _libsumo
            import sumolib as _sumolib

            traci = _libsumo
            sumolib = _sumolib
            SUMO_AVAILABLE = True
            USING_LIBSUMO = True
            print("[SUMO] Using libsumo (in-process, high performance)")
            _INITIALIZED = True
            return
        except Exception as exc:
            print(f"[SUMO] libsumo not used ({type(exc).__name__}: {exc}); falling back to traci")

    try:
        import traci as _traci
        import sumolib as _sumolib

        traci = _traci
        sumolib = _sumolib
        SUMO_AVAILABLE = True
        USING_LIBSUMO = False
        if force_traci:
            print("[SUMO] Using traci (forced via FORCE_TRACI)")
        else:
            print("[SUMO] Using traci (socket-based)")
    except ImportError:
        SUMO_AVAILABLE = False
        USING_LIBSUMO = False
        print("[SUMO] Neither libsumo nor traci found. Install: pip install eclipse-sumo")

    _INITIALIZED = True


# Auto-initialize on first import so downstream `from sumo_mgr.traci_compat import traci`
# always gets a usable object, even if main_complete_integration hasn't called init() yet.
init()
