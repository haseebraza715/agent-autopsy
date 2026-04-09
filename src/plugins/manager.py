"""
Plugin manager and registration mechanism.
"""

from __future__ import annotations

import importlib
from importlib.metadata import entry_points
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

from .base import (
    FixGeneratorPlugin,
    ParserPlugin,
    PatternDetectorPlugin,
    ReportTemplatePlugin,
    VisualizationPlugin,
)


class PluginManager:
    """Central plugin registry."""

    def __init__(self) -> None:
        self.parsers: list[ParserPlugin] = []
        self.pattern_detectors: list[PatternDetectorPlugin] = []
        self.report_templates: list[ReportTemplatePlugin] = []
        self.fix_generators: list[FixGeneratorPlugin] = []
        self.visualizations: list[VisualizationPlugin] = []
        self._loaded = False
        self.errors: list[str] = []

    def register_parser(self, plugin: ParserPlugin) -> None:
        self.parsers.append(plugin)

    def register_pattern_detector(self, plugin: PatternDetectorPlugin) -> None:
        self.pattern_detectors.append(plugin)

    def register_report_template(self, plugin: ReportTemplatePlugin) -> None:
        self.report_templates.append(plugin)

    def register_fix_generator(self, plugin: FixGeneratorPlugin) -> None:
        self.fix_generators.append(plugin)

    def register_visualization(self, plugin: VisualizationPlugin) -> None:
        self.visualizations.append(plugin)

    def ensure_loaded(self) -> None:
        """Load plugins from entry points and local plugin files once."""
        if self._loaded:
            return
        self._loaded = True
        self._load_entrypoint_plugins()
        self._load_local_plugins()

    def _load_entrypoint_plugins(self) -> None:
        """Load plugins from Python entry points."""
        groups = {
            "agent_autopsy.parsers": self.register_parser,
            "agent_autopsy.pattern_detectors": self.register_pattern_detector,
            "agent_autopsy.report_templates": self.register_report_template,
            "agent_autopsy.fix_generators": self.register_fix_generator,
            "agent_autopsy.visualizations": self.register_visualization,
        }
        eps = entry_points()
        for group_name, registrar in groups.items():
            for ep in eps.select(group=group_name):
                try:
                    plugin = ep.load()
                    instance = plugin() if isinstance(plugin, type) else plugin
                    registrar(instance)
                except Exception as exc:  # pragma: no cover - defensive for external plugins
                    self.errors.append(f"entrypoint {group_name}:{ep.name} failed: {exc}")

    def _load_local_plugins(self) -> None:
        """
        Load local plugins from filesystem.

        Expected:
            A directory path in AGENT_AUTOPSY_PLUGINS_DIR containing `.py` files
            that expose `register(plugin_manager)`.
        """
        plugins_dir = os.getenv("AGENT_AUTOPSY_PLUGINS_DIR", "").strip()
        if not plugins_dir:
            return
        path = Path(plugins_dir).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            self.errors.append(f"local plugin dir not found: {path}")
            return

        sys.path.insert(0, str(path))
        try:
            for py_file in sorted(path.glob("*.py")):
                module_name = py_file.stem
                try:
                    mod = importlib.import_module(module_name)
                    self._register_module(mod, module_name)
                except Exception as exc:  # pragma: no cover - defensive for external plugins
                    self.errors.append(f"local plugin {module_name} failed: {exc}")
        finally:
            if str(path) in sys.path:
                sys.path.remove(str(path))

    def _register_module(self, module: ModuleType, module_name: str) -> None:
        register_fn = getattr(module, "register", None)
        if callable(register_fn):
            register_fn(self)
        else:
            self.errors.append(f"local plugin {module_name} missing register(plugin_manager)")


_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    """Get global plugin manager."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    _plugin_manager.ensure_loaded()
    return _plugin_manager
