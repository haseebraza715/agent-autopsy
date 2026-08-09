"""API-level integration: load trace -> pre-analysis -> report pipeline (offline).

Exercises the public facade in ``agent_autopsy.api`` exactly the way the CLI,
Streamlit, and MCP entry points do, without spawning subprocesses.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_autopsy import api
from agent_autopsy.analysis.agent import AnalysisResult
from agent_autopsy.analysis.llm_cache import PROMPT_VERSION, cache_key, trace_digest
from agent_autopsy.errors import ParseError
from agent_autopsy.schema import TraceStatus
from agent_autopsy.utils.config import Config, get_config, set_config

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE = REPO_ROOT / "tests" / "sample_traces"
EXAMPLES = REPO_ROOT / "examples" / "traces"


@pytest.fixture(autouse=True)
def _restore_config() -> None:
    yield
    set_config(Config.from_env())


@pytest.fixture()
def loop_trace():
    return api.load_trace(SAMPLE / "loop_failure.json")


class TestLoadTrace:
    def test_load_and_normalize_sample(self) -> None:
        trace = api.load_trace(SAMPLE / "successful_run.json")
        assert trace.run_id == "run_success_001"
        assert trace.status == TraceStatus.SUCCESS
        assert [e.event_id for e in trace.events] == list(range(len(trace.events)))

    def test_load_from_dict(self) -> None:
        data = {
            "run_id": "inline-1",
            "status": "failed",
            "events": [
                {"type": "tool", "name": "search", "input": {"q": "x"}, "error": "boom"},
                {"type": "tool", "name": "search", "input": {"q": "x"}, "error": "boom"},
                {"type": "tool", "name": "search", "input": {"q": "x"}, "error": "boom"},
            ],
        }
        trace = api.load_trace_from_dict(data)
        assert trace.run_id == "inline-1"
        assert trace.status == TraceStatus.FAILED

    def test_load_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            api.load_trace(REPO_ROOT / "nope.json")


class TestFullPipeline:
    def test_analyze_pipeline_returns_report(self, tmp_path: Path) -> None:
        report = api.analyze(SAMPLE / "loop_failure.json", no_llm=True, no_embeddings=True)

        markdown = report.markdown()
        assert "Autopsy Report" in markdown
        assert "run_loop_001" in markdown
        assert "Root Cause Chain" in markdown

        payload = report.json_dict()
        assert payload["run_id"] == "run_loop_001"
        assert 0 <= payload["health_score"] <= 100
        assert payload["status"] == "failed"
        assert payload["evidence_events"]

    def test_analyze_respects_no_embeddings_and_restores_config(self) -> None:
        cfg = get_config()
        prev = cfg.skip_embeddings
        report = api.analyze(SAMPLE / "successful_run.json", no_llm=True, no_embeddings=True)
        assert report.analysis.success
        assert cfg.skip_embeddings == prev

    def test_render_report_formats(self) -> None:
        report = api.analyze(SAMPLE / "loop_failure.json", no_llm=True, no_embeddings=True)
        assert "Autopsy Report" in api.render_report(report, "markdown")
        assert "run_loop_001" in api.render_report(report, "json")
        assert "Autopsy Report" in api.render_report(report, "text")
        # "text" should have markdown heading markers stripped
        assert "\n# " not in api.render_report(report, "text").split("Autopsy Report")[0]

    def test_examples_directory_end_to_end(self) -> None:
        for example in ["loop_failure.json", "hallucinated_tool.json", "successful_run.json", "loop_fixed.json"]:
            report = api.analyze(EXAMPLES / example, no_llm=True, no_embeddings=True)
            assert report.report_generator.to_json()["run_id"], example


class TestDeterministicAnalysis:
    def test_deterministic_analysis_on_failed_trace(self) -> None:
        trace = api.load_trace(SAMPLE / "loop_failure.json")
        result = api.run_deterministic_analysis(trace)
        assert isinstance(result, AnalysisResult)
        assert result.success
        assert "## Findings" in result.report
        assert result.preanalysis["signals"]

    def test_deterministic_analysis_on_clean_trace(self) -> None:
        trace = api.load_trace(SAMPLE / "successful_run.json")
        result = api.run_deterministic_analysis(trace)
        assert result.success
        assert "No deterministic failure patterns" in result.report


class TestReportPersistence:
    def test_save_report_infers_extension(self, tmp_path: Path) -> None:
        report = api.analyze(SAMPLE / "successful_run.json", no_llm=True, no_embeddings=True)
        gen = api.generate_report(report.trace, report.analysis)

        md_path = gen.save(tmp_path / "out")
        assert md_path.suffix == ".md"

        json_path = gen.save(tmp_path / "out2", format="json")
        assert json_path.suffix == ".json"
        json.loads(json_path.read_text())

        text_path = gen.save(tmp_path / "out3", format="text")
        assert text_path.suffix == ".txt"

    def test_save_report_creates_parent_dirs(self, tmp_path: Path) -> None:
        report = api.analyze(SAMPLE / "successful_run.json", no_llm=True, no_embeddings=True)
        gen = api.generate_report(report.trace, report.analysis)
        path = gen.save(tmp_path / "deep" / "nested" / "report.md")
        assert path.is_file()


class TestCredentials:
    @pytest.mark.parametrize(
        ("provider", "config_key", "env", "expected"),
        [
            ("openrouter", "sk-openrouter", {}, True),
            ("openrouter", None, {}, False),
            ("openai", None, {"OPENAI_API_KEY": "sk-test"}, True),
            ("openai", None, {}, False),
            ("anthropic", None, {"ANTHROPIC_API_KEY": "sk-ant"}, True),
            ("anthropic", None, {}, False),
            ("ollama", None, {}, True),
            ("unknown", None, {}, False),
        ],
    )
    def test_llm_credentials_configured(
        self,
        monkeypatch: pytest.MonkeyPatch,
        provider: str,
        config_key: str | None,
        env: dict,
        expected: bool,
    ) -> None:
        for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)

        cfg = Config.from_env()
        cfg.llm_provider = provider
        if config_key:
            cfg.openrouter_api_key = config_key
        assert api.llm_credentials_configured(cfg) is expected


class TestCacheKeyStability:
    def test_digest_stable_across_calls(self) -> None:
        trace = api.load_trace(SAMPLE / "successful_run.json")
        assert trace_digest(trace) == trace_digest(trace)

    def test_cache_key_incorporates_model_and_prompt_version(self) -> None:
        trace = api.load_trace(SAMPLE / "successful_run.json")
        k1 = cache_key(trace, "model-a")
        k2 = cache_key(trace, "model-b")
        k3 = cache_key(trace, "model-a", prompt_version="other")
        assert k1 != k2
        assert k1 != k3
        assert k1 == cache_key(trace, "model-a", prompt_version=PROMPT_VERSION)

    def test_trace_summary_shape(self) -> None:
        trace = api.load_trace(SAMPLE / "loop_failure.json")
        summary = api.trace_summary(trace)
        for key in ["run_id", "status", "total_events", "llm_calls", "tool_calls", "errors", "framework"]:
            assert key in summary
        assert summary["total_events"] == 11


class TestErrorPaths:
    def test_parse_error_message_includes_path(self, tmp_path: Path) -> None:
        bad = tmp_path / "broken.json"
        bad.write_text("{not json", encoding="utf-8")
        with pytest.raises(ParseError, match="Invalid JSON"):
            api.load_trace(bad)

    def test_parse_empty_file_raises_parse_error(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.json"
        empty.write_text("", encoding="utf-8")
        with pytest.raises(ParseError):
            api.load_trace(empty)
