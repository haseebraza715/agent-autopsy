"""Deterministic property-style tests: seeded random traces must always satisfy
normalizer/detector/report invariants. No hypothesis dependency, no network."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from agent_autopsy.ingestion import TraceNormalizer, parse_trace_data
from agent_autopsy.preanalysis import PatternDetector, RootCauseBuilder

_SEED = 20260809
_TOOL_NAMES = ["search", "calculator", "db_lookup", "send_email", "web_fetch"]
_EVENT_TYPES = ["llm", "tool", "message", "error", "decision"]


def _random_trace(rng: random.Random, n_events: int) -> dict:
    events = []
    base = datetime(2026, 1, 1, 0, 0, 0)
    for i in range(n_events):
        etype = rng.choice(_EVENT_TYPES)
        event: dict = {"type": etype}
        if etype in ("llm", "tool"):
            event["name"] = rng.choice(_TOOL_NAMES)
        event["input"] = {"q": rng.choice(["alpha", "beta", "gamma"])}
        if rng.random() < 0.3:
            event["output"] = {"ok": rng.randint(0, 100)}
        if rng.random() < 0.2:
            event["error"] = {"message": rng.choice(["timeout", "401 unauthorized", "boom"])}
        if rng.random() < 0.8:
            event["timestamp"] = (base + timedelta(seconds=rng.randint(0, 1000))).isoformat() + "Z"
        if rng.random() < 0.3:
            event["latency_ms"] = rng.randint(0, 300_000)
        if rng.random() < 0.3:
            event["token_count"] = rng.randint(0, 50_000)
        events.append(event)
    return {
        "run_id": f"prop-{rng.randint(0, 10**9):09d}",
        "status": rng.choice(["success", "failed", "timeout"]),
        "tools": rng.sample(_TOOL_NAMES, rng.randint(1, len(_TOOL_NAMES))),
        "goal": rng.choice(["build quarterly report", "fix the bug", "summarize docs"]),
        "events": events,
    }


def _cases(n: int, rng: random.Random) -> list[dict]:
    return [_random_trace(rng, rng.randint(0, 80)) for _ in range(n)]


class TestNormalizerInvariants:
    def test_all_random_traces_normalize(self) -> None:
        rng = random.Random(_SEED)
        for raw in _cases(60, rng):
            trace = parse_trace_data(raw)
            normalized = TraceNormalizer.normalize(trace)
            assert [e.event_id for e in normalized.events] == list(range(len(normalized.events)))
            # stats must match a fresh recalculation
            recalculated = TraceNormalizer.calculate_stats(normalized)
            assert recalculated.model_dump() == normalized.stats.model_dump()
            # hard validation issues must never appear after normalization
            issues = TraceNormalizer.validate(normalized)
            assert not [i for i in issues if "precedes" not in i]

    def test_stats_match_event_counters(self) -> None:
        rng = random.Random(_SEED + 1)
        for raw in _cases(40, rng):
            trace = TraceNormalizer.normalize(parse_trace_data(raw))
            from agent_autopsy.schema import EventType

            assert trace.stats.num_llm_calls == sum(1 for e in trace.events if e.type == EventType.LLM_CALL)
            assert trace.stats.num_tool_calls == sum(1 for e in trace.events if e.type == EventType.TOOL_CALL)
            assert trace.stats.num_errors == sum(1 for e in trace.events if e.is_error())

    def test_normalize_twice_is_stable(self) -> None:
        rng = random.Random(_SEED + 2)
        for raw in _cases(30, rng):
            trace = parse_trace_data(raw)
            TraceNormalizer.normalize(trace)
            first = trace.model_dump()
            TraceNormalizer.normalize(trace)
            assert trace.model_dump() == first

    def test_detectors_never_crash_on_random_traces(self) -> None:
        rng = random.Random(_SEED + 3)
        for raw in _cases(60, rng):
            trace = TraceNormalizer.normalize(parse_trace_data(raw))
            patterns = PatternDetector(trace).detect_all()
            for pattern in patterns:
                assert isinstance(pattern.pattern_type.value, str)
                assert isinstance(pattern.severity.value, str)
                assert all(isinstance(eid, int) for eid in pattern.event_ids)

    def test_preanalysis_bundle_is_serializable(self) -> None:
        rng = random.Random(_SEED + 4)
        for raw in _cases(30, rng):
            trace = TraceNormalizer.normalize(parse_trace_data(raw))
            bundle = RootCauseBuilder(trace).build()
            dumped = bundle.to_dict()
            assert isinstance(dumped["summary"], str)
            assert isinstance(dumped["signals"], list)
            assert isinstance(dumped["top_suspects"], list)
            for signal in dumped["signals"]:
                assert set(signal) >= {"type", "severity", "evidence", "events"}


class TestDeterministicReports:
    def test_deterministic_report_renders_for_all_random_traces(self) -> None:
        from agent_autopsy.output.deterministic_report import render_deterministic_markdown

        rng = random.Random(_SEED + 5)
        for raw in _cases(25, rng):
            trace = TraceNormalizer.normalize(parse_trace_data(raw))
            bundle = RootCauseBuilder(trace).build()
            markdown = render_deterministic_markdown(trace, bundle)
            assert "# Autopsy Report" in markdown
            assert "## Findings" in markdown

    def test_report_generator_handles_random_traces(self) -> None:
        from agent_autopsy.analysis.agent import AnalysisResult
        from agent_autopsy.output import ReportGenerator

        rng = random.Random(_SEED + 6)
        for raw in _cases(25, rng):
            trace = TraceNormalizer.normalize(parse_trace_data(raw))
            bundle = RootCauseBuilder(trace).build()
            result = AnalysisResult(
                report="",
                trace_summary=TraceNormalizer.get_summary(trace),
                preanalysis=bundle.to_dict(),
                success=True,
            )
            report = ReportGenerator(trace, result).generate()
            assert 0 <= report.health_score <= 100
            assert 0.0 <= report.confidence <= 1.0
            assert report.run_id == trace.run_id


class TestSignatureStability:
    def test_signature_stable_across_random_inputs(self) -> None:
        rng = random.Random(_SEED + 7)
        for raw in _cases(30, rng):
            trace = TraceNormalizer.normalize(parse_trace_data(raw))
            for event in trace.get_tool_calls():
                sig = event.get_tool_signature()
                if sig:
                    assert event.get_tool_signature() == sig


class TestEmptyAndDegenerate:
    def test_all_empty_trace_variants(self) -> None:
        for raw in [{}, {"run_id": "x"}, {"run_id": "x", "events": []}, {"status": "failed", "events": []}]:
            trace = TraceNormalizer.normalize(parse_trace_data(raw))
            bundle = RootCauseBuilder(trace).build()
            assert PatternDetector(trace).detect_all() == []
            assert bundle.summary  # non-empty
