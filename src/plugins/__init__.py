"""Plugin interfaces and manager."""

from .base import (
    ParserPlugin,
    PatternDetectorPlugin,
    ReportTemplatePlugin,
    FixGeneratorPlugin,
    VisualizationPlugin,
)
from .manager import PluginManager, get_plugin_manager

__all__ = [
    "ParserPlugin",
    "PatternDetectorPlugin",
    "ReportTemplatePlugin",
    "FixGeneratorPlugin",
    "VisualizationPlugin",
    "PluginManager",
    "get_plugin_manager",
]
