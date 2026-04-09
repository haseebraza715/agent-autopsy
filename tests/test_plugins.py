"""Tests for plugin loading and parser integration."""

from __future__ import annotations

from pathlib import Path

from src.ingestion.parser import TraceParser, parse_trace_data
from src.plugins import manager as plugin_manager_module
from src.plugins import get_plugin_manager


def _reset_global_plugin_manager() -> None:
    plugin_manager_module._plugin_manager = None


def test_local_parser_plugin_is_loaded(monkeypatch, tmp_path: Path):
    plugin_file = tmp_path / "custom_parser.py"
    plugin_file.write_text(
        "\n".join(
            [
                "from datetime import datetime",
                "from src.plugins import ParserPlugin",
                "from src.schema import EnvironmentInfo, Trace, TraceStatus",
                "",
                "class CustomParser(ParserPlugin):",
                "    name = 'custom_json'",
                "",
                "    def can_parse(self, data):",
                "        return data.get('format') == 'custom_json'",
                "",
                "    def parse(self, data):",
                "        return Trace(",
                "            run_id=data.get('run_id', 'custom-run'),",
                "            timestamp_start=datetime(2026, 1, 1, 0, 0, 0),",
                "            status=TraceStatus.SUCCESS,",
                "            env=EnvironmentInfo(agent_framework='custom'),",
                "            events=[],",
                "        )",
                "",
                "def register(plugin_manager):",
                "    plugin_manager.register_parser(CustomParser())",
            ]
        )
    )

    monkeypatch.setenv("AGENT_AUTOPSY_PLUGINS_DIR", str(tmp_path))
    _reset_global_plugin_manager()

    manager = get_plugin_manager()
    assert any(plugin.name == "custom_json" for plugin in manager.parsers)

    detected = TraceParser.detect_format({"format": "custom_json", "run_id": "p-1"})
    parsed = parse_trace_data({"format": "custom_json", "run_id": "p-1"})

    assert detected == "plugin:custom_json"
    assert parsed.run_id == "p-1"
    assert parsed.env.agent_framework == "custom"

    _reset_global_plugin_manager()


def test_plugin_manager_records_missing_register_error(monkeypatch, tmp_path: Path):
    plugin_file = tmp_path / "broken_plugin.py"
    plugin_file.write_text("x = 1\n")

    monkeypatch.setenv("AGENT_AUTOPSY_PLUGINS_DIR", str(tmp_path))
    _reset_global_plugin_manager()

    manager = get_plugin_manager()

    assert any("missing register" in error for error in manager.errors)

    _reset_global_plugin_manager()
