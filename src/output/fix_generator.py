"""
Advanced fix suggestion generation.

Produces trace-tailored fix suggestions and patch snippets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.preanalysis import PreAnalysisBundle
from src.schema import Trace


@dataclass
class FixSuggestion:
    """A generated fix suggestion."""

    title: str
    category: str
    rationale: str
    patch_snippet: str
    event_ids: list[int]


class FixSuggestionGenerator:
    """Generate actionable, trace-aware fix suggestions."""

    def __init__(self, trace: Trace, preanalysis: PreAnalysisBundle):
        self.trace = trace
        self.preanalysis = preanalysis

    def generate(self) -> list[FixSuggestion]:
        suggestions: list[FixSuggestion] = []
        signals = self.preanalysis.signals
        available_tools = self.trace.env.tools_available

        for signal in signals:
            if signal.type == "infinite_loop":
                node = self._guess_loop_node(signal.event_ids)
                suggestions.append(
                    FixSuggestion(
                        title="Add max-iteration guard to looping node",
                        category="code",
                        rationale="Identical tool calls repeated consecutively indicate missing termination criteria.",
                        patch_snippet=(
                            f"# candidate node: {node}\n"
                            "state['iteration_count'] = state.get('iteration_count', 0) + 1\n"
                            "if state['iteration_count'] > MAX_ITERATIONS:\n"
                            "    raise RuntimeError('Loop guard triggered')\n"
                        ),
                        event_ids=signal.event_ids,
                    )
                )
            elif signal.type == "hallucinated_tool":
                tools_text = ", ".join(available_tools) if available_tools else "<declare tools>"
                suggestions.append(
                    FixSuggestion(
                        title="Harden system prompt with explicit tool allow-list",
                        category="prompt",
                        rationale="Tool hallucination can be reduced with explicit allowed tool names and policy.",
                        patch_snippet=(
                            "You may only call these tools:\n"
                            f"{tools_text}\n"
                            "If required functionality is unavailable, ask for guidance instead of inventing tools.\n"
                        ),
                        event_ids=signal.event_ids,
                    )
                )
            elif signal.type == "error_cascade":
                root_tool = self._guess_root_error_tool(signal.event_ids)
                suggestions.append(
                    FixSuggestion(
                        title="Wrap failing tool calls with local error boundary",
                        category="code",
                        rationale="Error cascades indicate one failure propagates without containment.",
                        patch_snippet=(
                            f"def safe_{root_tool}(**kwargs):\n"
                            "    try:\n"
                            f"        return {root_tool}(**kwargs)\n"
                            "    except Exception as exc:\n"
                            "        return {'ok': False, 'error': str(exc), 'retryable': False}\n"
                        ),
                        event_ids=signal.event_ids,
                    )
                )
            elif signal.type == "context_overflow":
                suggestions.append(
                    FixSuggestion(
                        title="Add adaptive context windowing",
                        category="ops",
                        rationale="Context overflow indicates prompt assembly exceeds model limits.",
                        patch_snippet=(
                            "def build_context(history, max_tokens):\n"
                            "    while estimate_tokens(history) > max_tokens:\n"
                            "        history = summarize_oldest_chunk(history)\n"
                            "    return history\n"
                        ),
                        event_ids=signal.event_ids,
                    )
                )

        # Deduplicate by title + category
        seen: set[tuple[str, str]] = set()
        deduped: list[FixSuggestion] = []
        for suggestion in suggestions:
            key = (suggestion.title, suggestion.category)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(suggestion)
        return deduped

    def to_dict(self) -> list[dict[str, Any]]:
        """Serialize suggestions to dictionaries."""
        return [
            {
                "title": suggestion.title,
                "category": suggestion.category,
                "rationale": suggestion.rationale,
                "patch_snippet": suggestion.patch_snippet,
                "event_ids": suggestion.event_ids,
            }
            for suggestion in self.generate()
        ]

    def _guess_loop_node(self, event_ids: list[int]) -> str:
        for event_id in event_ids:
            event = self.trace.get_event(event_id)
            if event and event.name:
                return event.name
        return "router_or_loop_node"

    def _guess_root_error_tool(self, event_ids: list[int]) -> str:
        for event_id in event_ids:
            event = self.trace.get_event(event_id)
            if event and event.name:
                return event.name.replace("-", "_")
        return "tool_call"
