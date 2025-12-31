"""
Base parser interface and factory for trace parsing.

This module provides the abstract base class for trace parsers
and a factory function to select the appropriate parser based on format.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.schema import Trace


class TraceParser(ABC):
    """Abstract base class for trace parsers."""

    @abstractmethod
    def can_parse(self, data: dict[str, Any]) -> bool:
        """Check if this parser can handle the given data."""
        pass

    @abstractmethod
    def parse(self, data: dict[str, Any]) -> Trace:
        """Parse the data into a normalized Trace."""
        pass

    @classmethod
    def detect_format(cls, data: dict[str, Any]) -> str:
        """Detect the format of the trace data."""
        # LangGraph detection
        if "thread_id" in data or "checkpoint" in data:
            return "langgraph"
        if "runs" in data and isinstance(data["runs"], list):
            return "langgraph"

        # LangChain detection
        if "run_type" in data and data.get("run_type") in ["chain", "llm", "tool"]:
            return "langchain"
        if "callbacks" in data:
            return "langchain"

        # OpenTelemetry detection
        if "resourceSpans" in data or "traceId" in data:
            return "opentelemetry"

        return "generic"


def parse_trace_file(file_path: str | Path) -> Trace:
    """
    Parse a trace file and return a normalized Trace.

    This is the main entry point for trace parsing.
    It auto-detects the format and uses the appropriate parser.

    Args:
        file_path: Path to the trace JSON file

    Returns:
        Normalized Trace object
    """
    from .formats.langgraph import LangGraphParser
    from .formats.generic import GenericJSONParser

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Trace file not found: {path}")

    with open(path, "r") as f:
        data = json.load(f)

    # Detect format and select parser
    format_type = TraceParser.detect_format(data)

    parsers: dict[str, TraceParser] = {
        "langgraph": LangGraphParser(),
        "generic": GenericJSONParser(),
    }

    parser = parsers.get(format_type, GenericJSONParser())

    if not parser.can_parse(data):
        # Fallback to generic parser
        parser = GenericJSONParser()

    return parser.parse(data)
