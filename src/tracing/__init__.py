"""
Trace capture module for Agent Autopsy.

Provides automatic trace capture for LangChain/LangGraph agents.
"""

from .trace_saver import (
    TraceSaver,
    start_trace,
    end_trace,
    get_trace_config,
)

__all__ = [
    "TraceSaver",
    "start_trace",
    "end_trace",
    "get_trace_config",
]
