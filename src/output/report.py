"""
Report generation for Agent Autopsy.

Generates structured markdown reports from analysis results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.schema import Trace
from src.analysis.agent import AnalysisResult


@dataclass
class AutopsyReport:
    """Structured autopsy report."""
    run_id: str
    status: str
    generated_at: datetime
    summary: str
    timeline: list[str]
    root_cause_chain: list[str]
    fix_recommendations: dict[str, list[str]]
    confidence: float
    evidence_events: list[int]
    raw_report: str
    preanalysis: dict = field(default_factory=dict)
    trace_summary: dict = field(default_factory=dict)


class ReportGenerator:
    """
    Generates autopsy reports from analysis results.

    Supports multiple output formats (markdown, JSON).
    """

    def __init__(self, trace: Trace, analysis_result: AnalysisResult):
        self.trace = trace
        self.result = analysis_result

    def generate(self) -> AutopsyReport:
        """Generate the autopsy report."""
        return AutopsyReport(
            run_id=self.trace.run_id,
            status=self.trace.status.value,
            generated_at=datetime.now(),
            summary=self._extract_summary(),
            timeline=self._extract_timeline(),
            root_cause_chain=self._extract_root_causes(),
            fix_recommendations=self._extract_fixes(),
            confidence=self._extract_confidence(),
            evidence_events=self._extract_evidence_events(),
            raw_report=self.result.report,
            preanalysis=self.result.preanalysis,
            trace_summary=self.result.trace_summary,
        )

    def _extract_summary(self) -> str:
        """Extract summary from report."""
        report = self.result.report
        if "## Summary" in report:
            start = report.find("## Summary")
            end = report.find("##", start + 10)
            if end == -1:
                end = len(report)
            return report[start:end].replace("## Summary", "").strip()
        return f"Analysis of run {self.trace.run_id} - Status: {self.trace.status.value}"

    def _extract_timeline(self) -> list[str]:
        """Extract timeline from report or generate from trace."""
        timeline = []

        # Try to extract from report
        report = self.result.report
        if "## Timeline" in report or "## What happened" in report:
            # Parse timeline section
            pass

        # Generate basic timeline from trace
        if not timeline:
            for event in self.trace.events[:10]:  # First 10 events
                desc = f"Event {event.event_id}: {event.type.value}"
                if event.name:
                    desc += f" - {event.name}"
                if event.is_error():
                    desc += " [ERROR]"
                timeline.append(desc)

            if len(self.trace.events) > 10:
                timeline.append(f"... ({len(self.trace.events) - 10} more events)")

        return timeline

    def _extract_root_causes(self) -> list[str]:
        """Extract root cause chain from analysis."""
        causes = []

        # From preanalysis hypotheses
        hypotheses = self.result.preanalysis.get("top_suspects", [])
        for hyp in hypotheses[:3]:  # Top 3
            causes.append(f"{hyp.get('hypothesis', 'Unknown')} (confidence: {hyp.get('confidence', 0):.0%})")

        return causes if causes else ["Root cause analysis incomplete"]

    def _extract_fixes(self) -> dict[str, list[str]]:
        """Extract fix recommendations categorized by type."""
        fixes = {
            "code": [],
            "tool": [],
            "prompt": [],
            "ops": [],
        }

        # From preanalysis
        hypotheses = self.result.preanalysis.get("top_suspects", [])
        for hyp in hypotheses:
            category = hyp.get("category", "code")
            suggested = hyp.get("suggested_fixes", [])
            if category in fixes:
                fixes[category].extend(suggested)
            else:
                fixes["code"].extend(suggested)

        # Deduplicate
        for category in fixes:
            fixes[category] = list(set(fixes[category]))

        return fixes

    def _extract_confidence(self) -> float:
        """Extract confidence score from analysis."""
        hypotheses = self.result.preanalysis.get("top_suspects", [])
        if hypotheses:
            return hypotheses[0].get("confidence", 0.5)
        return 0.5

    def _extract_evidence_events(self) -> list[int]:
        """Extract event IDs cited as evidence."""
        events = set()

        # From preanalysis signals
        signals = self.result.preanalysis.get("signals", [])
        for signal in signals:
            events.update(signal.get("events", []))

        # From hypotheses
        hypotheses = self.result.preanalysis.get("top_suspects", [])
        for hyp in hypotheses:
            events.update(hyp.get("supporting_events", []))

        return sorted(list(events))

    def to_markdown(self) -> str:
        """Generate markdown report."""
        report = self.generate()

        lines = [
            f"# Autopsy Report: Run {report.run_id}",
            "",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"- **Status:** {report.status}",
            f"- **Confidence:** {report.confidence:.0%}",
            "",
            report.summary,
            "",
            "---",
            "",
            "## Timeline",
            "",
        ]

        for item in report.timeline:
            lines.append(f"- {item}")

        lines.extend([
            "",
            "---",
            "",
            "## Root Cause Chain",
            "",
        ])

        for i, cause in enumerate(report.root_cause_chain, 1):
            lines.append(f"{i}. {cause}")

        lines.extend([
            "",
            "---",
            "",
            "## Fix Recommendations",
            "",
        ])

        category_labels = {
            "code": "A) Graph/Code Fixes",
            "tool": "B) Tool Contract Fixes",
            "prompt": "C) Prompt/Policy Fixes",
            "ops": "D) Ops Fixes",
        }

        for category, label in category_labels.items():
            fixes = report.fix_recommendations.get(category, [])
            if fixes:
                lines.append(f"### {label}")
                lines.append("")
                for fix in fixes:
                    lines.append(f"- {fix}")
                lines.append("")

        lines.extend([
            "---",
            "",
            "## Evidence",
            "",
            f"**Cited Events:** {report.evidence_events}",
            "",
            "---",
            "",
            "## Trace Statistics",
            "",
        ])

        stats = report.trace_summary
        lines.extend([
            f"- Total Events: {stats.get('total_events', 'N/A')}",
            f"- LLM Calls: {stats.get('llm_calls', 'N/A')}",
            f"- Tool Calls: {stats.get('tool_calls', 'N/A')}",
            f"- Errors: {stats.get('errors', 'N/A')}",
            f"- Total Tokens: {stats.get('total_tokens', 'N/A')}",
            f"- Duration: {stats.get('duration_ms', 'N/A')} ms",
            "",
        ])

        # Add LLM report if available
        if report.raw_report and "deterministic" not in report.raw_report.lower():
            lines.extend([
                "---",
                "",
                "## Detailed Analysis",
                "",
                report.raw_report,
            ])

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """Generate JSON report."""
        report = self.generate()

        return {
            "run_id": report.run_id,
            "status": report.status,
            "generated_at": report.generated_at.isoformat(),
            "summary": report.summary,
            "timeline": report.timeline,
            "root_cause_chain": report.root_cause_chain,
            "fix_recommendations": report.fix_recommendations,
            "confidence": report.confidence,
            "evidence_events": report.evidence_events,
            "trace_summary": report.trace_summary,
            "preanalysis": report.preanalysis,
        }

    def save(self, path: str | Path, format: str = "markdown") -> Path:
        """Save report to file."""
        path = Path(path)

        if format == "markdown":
            content = self.to_markdown()
            if not path.suffix:
                path = path.with_suffix(".md")
        elif format == "json":
            import json
            content = json.dumps(self.to_json(), indent=2, default=str)
            if not path.suffix:
                path = path.with_suffix(".json")
        else:
            raise ValueError(f"Unknown format: {format}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

        return path
