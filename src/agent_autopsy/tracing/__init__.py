"""
Trace capture module for Agent Autopsy.

Provides automatic trace capture for LangChain/LangGraph agents.
"""

from .trace_saver import (
    TraceSaver,
    end_trace,
    get_trace_config,
    start_trace,
)

__all__ = [
    "TraceSaver",
    "end_trace",
    "get_trace_config",
    "start_trace",
]
