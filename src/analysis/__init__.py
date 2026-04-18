from __future__ import annotations

from typing import Any

from .agent import AnalysisResult, ReportQualityValidator, run_analysis_without_llm
from .prompts import SYSTEM_PROMPT, get_analysis_prompt
from .tools import create_analysis_tools

__all__ = [
    "AnalysisAgent",
    "AnalysisResult",
    "ReportQualityValidator",
    "run_analysis",
    "run_analysis_stream",
    "run_analysis_without_llm",
    "create_analysis_tools",
    "SYSTEM_PROMPT",
    "get_analysis_prompt",
]


def __getattr__(name: str) -> Any:
    """Lazy-load LangGraph/LangChain-backed symbols so ``--no-llm`` stays lightweight."""
    if name == "AnalysisAgent":
        from .llm_agent import AnalysisAgent

        return AnalysisAgent
    if name == "run_analysis":
        from .llm_agent import run_analysis

        return run_analysis
    if name == "run_analysis_stream":
        from .llm_agent import run_analysis_stream

        return run_analysis_stream
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
