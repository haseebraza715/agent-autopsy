"""
Plugin interfaces for Agent Autopsy extensibility.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from src.analysis.agent import AnalysisResult
    from src.preanalysis.suspects import PreAnalysisBundle
    from src.schema import Trace
    from src.preanalysis.patterns import PatternResult


class ParserPlugin(ABC):
    """Plugin interface for custom trace parsers."""

    name: str = "unnamed_parser"

    @abstractmethod
    def can_parse(self, data: dict[str, Any]) -> bool:
        """Return True when plugin can parse payload."""

    @abstractmethod
    def parse(self, data: dict[str, Any]) -> "Trace":
        """Parse payload into normalized Trace."""


class PatternDetectorPlugin(ABC):
    """Plugin interface for custom deterministic detectors."""

    name: str = "unnamed_detector"

    @abstractmethod
    def detect(self, trace: "Trace") -> list["PatternResult"]:
        """Return plugin-detected pattern results."""


class ReportTemplatePlugin(ABC):
    """Plugin interface for custom report renderers."""

    format_name: str = "custom"

    @abstractmethod
    def render(self, trace: "Trace", analysis_result: "AnalysisResult") -> str:
        """Render report string for custom format."""


class FixGeneratorPlugin(ABC):
    """Plugin interface for custom fix suggestion generation."""

    name: str = "unnamed_fix_generator"

    @abstractmethod
    def generate(self, trace: "Trace", preanalysis: "PreAnalysisBundle") -> dict[str, Any]:
        """Return framework-specific fix suggestions."""


class VisualizationPlugin(ABC):
    """Plugin interface for custom visualizations."""

    name: str = "unnamed_visualization"

    @abstractmethod
    def build(self, trace: "Trace") -> dict[str, Any]:
        """Return visualization payload for UI consumption."""
