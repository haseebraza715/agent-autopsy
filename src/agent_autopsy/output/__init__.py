"""Output package: lazy exports avoid import cycles with ``src.analysis.agent``."""

from __future__ import annotations

from typing import Any

__all__ = [
    "ArtifactGenerator",
    "AutopsyReport",
    "FixSuggestionGenerator",
    "ReportGenerator",
]


def __getattr__(name: str) -> Any:
    if name in ("ReportGenerator", "AutopsyReport"):
        from . import report as _report

        if name == "ReportGenerator":
            return _report.ReportGenerator
        return _report.AutopsyReport
    if name == "ArtifactGenerator":
        from .artifacts import ArtifactGenerator

        return ArtifactGenerator
    if name == "FixSuggestionGenerator":
        from .fix_generator import FixSuggestionGenerator

        return FixSuggestionGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
