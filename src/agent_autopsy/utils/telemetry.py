"""
Opt-in anonymous CLI telemetry (off by default).

Records which commands ran and coarse outcome — never trace contents or API keys.
Enable with ``autopsy telemetry on`` or env ``AUTOPSY_TELEMETRY=1``.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_STATE_NAME = "telemetry_state.json"
_EVENTS_NAME = "telemetry-events.jsonl"


def _cache_root() -> Path:
    p = Path.home() / ".cache" / "agent-autopsy"
    p.mkdir(parents=True, exist_ok=True)
    return p


def state_path() -> Path:
    return _cache_root() / _STATE_NAME


def events_path() -> Path:
    return _cache_root() / _EVENTS_NAME


def _load_state() -> dict[str, Any]:
    path = state_path()
    if not path.is_file():
        return {"enabled": False}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {"enabled": False}


def is_enabled() -> bool:
    if os.getenv("AUTOPSY_TELEMETRY", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    return bool(_load_state().get("enabled"))


def set_enabled(on: bool) -> None:
    path = state_path()
    data = _load_state()
    data["enabled"] = on
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, indent=2))


def record_event(
    command: str,
    *,
    exit_code: int,
    signal_count: int = 0,
    run_id: str | None = None,
    duration_ms: float | None = None,
) -> None:
    """Append one JSON line if telemetry is enabled."""
    if not is_enabled():
        return
    rid_hash = None
    if run_id:
        rid_hash = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:16]
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "exit_code": exit_code,
        "signal_count": signal_count,
        "run_id_sha16": rid_hash,
        "duration_ms": duration_ms,
    }
    with events_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")
