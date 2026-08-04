"""Plugin interfaces and manager."""

from .base import (
    FixGeneratorPlugin,
    ParserPlugin,
    PatternDetectorPlugin,
    ReportTemplatePlugin,
    VisualizationPlugin,
)
from .manager import PluginManager, get_plugin_manager

__all__ = [
    "FixGeneratorPlugin",
    "ParserPlugin",
    "PatternDetectorPlugin",
    "PluginManager",
    "ReportTemplatePlugin",
    "VisualizationPlugin",
    "get_plugin_manager",
]
