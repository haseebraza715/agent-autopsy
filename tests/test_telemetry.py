"""Telemetry state (opt-in)."""

import json
from pathlib import Path

import pytest

from agent_autopsy.utils import telemetry as tel


def test_telemetry_default_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOPSY_TELEMETRY", "")
    root = tmp_path / "c"
    root.mkdir()
    monkeypatch.setattr(tel, "_cache_root", lambda: root)
    assert tel.is_enabled() is False
    tel.record_event("analyze", exit_code=0, signal_count=0)
    assert not tel.events_path().exists()


def test_telemetry_records_when_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOPSY_TELEMETRY", "")
    root = tmp_path / "c"
    root.mkdir()
    monkeypatch.setattr(tel, "_cache_root", lambda: root)
    tel.set_enabled(True)
    assert tel.is_enabled() is True
    tel.record_event("analyze", exit_code=1, signal_count=2, run_id="run-abc")
    log = tel.events_path()
    assert log.is_file()
    row = json.loads(log.read_text().strip().splitlines()[0])
    assert row["command"] == "analyze"
    assert row["exit_code"] == 1
    assert row["signal_count"] == 2
    assert row["run_id_sha16"]
