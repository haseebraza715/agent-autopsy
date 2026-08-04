"""
Structured LLM output: JSON schema + validation against trace event IDs.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from agent_autopsy.schema import Trace

logger = logging.getLogger(__name__)


class EvidenceItem(BaseModel):
    """Single piece of cited evidence."""

    description: str = Field(..., min_length=1)
    event_ids: list[int] = Field(default_factory=list)


class StructuredLLMReport(BaseModel):
    """Machine-readable capstone for synthesis (optional JSON block in LLM output)."""

    root_cause: str = Field(..., min_length=1)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("recommendations", mode="before")
    @classmethod
    def _strip_empty(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        return [str(x).strip() for x in v if str(x).strip()]


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def extract_structured_json(markdown_text: str) -> StructuredLLMReport | None:
    """Parse first fenced JSON block into :class:`StructuredLLMReport`, or return None."""
    if not markdown_text:
        return None
    m = _JSON_FENCE_RE.search(markdown_text)
    if not m:
        return None
    raw = m.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.debug("Structured JSON block not valid JSON")
        return None
    try:
        return StructuredLLMReport.model_validate(data)
    except Exception as exc:
        logger.debug("Structured JSON failed validation: %s", exc)
        return None


def validate_structured_against_trace(structured: StructuredLLMReport, trace: Trace) -> list[str]:
    """Return human-readable errors for event_ids not present on the trace."""
    valid = {e.event_id for e in trace.events}
    errors: list[str] = []
    for i, ev in enumerate(structured.evidence):
        for eid in ev.event_ids:
            if eid not in valid:
                errors.append(f"evidence[{i}] cites missing event_id={eid}")
    return errors


def structured_to_markdown_append(structured: StructuredLLMReport, validation_errors: list[str]) -> str:
    """Render validated (or partially invalid) structured object as markdown appendix."""
    lines = [
        "",
        "---",
        "",
        "## Structured summary (JSON, validated)",
        "",
        f"**Root cause:** {structured.root_cause}",
        f"**Confidence:** {structured.confidence:.2f}",
        "",
        "### Evidence",
        "",
    ]
    for ev in structured.evidence:
        ids = ", ".join(str(x) for x in ev.event_ids) or "(none)"
        lines.append(f"- {ev.description} _(events: {ids})_")
    lines.extend(["", "### Recommendations", ""])
    for r in structured.recommendations:
        lines.append(f"- {r}")
    if validation_errors:
        lines.extend(["", "**Validation:**", ""])
        for err in validation_errors:
            lines.append(f"- {err}")
    return "\n".join(lines)
