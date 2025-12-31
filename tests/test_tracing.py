"""Tests for the trace capture module."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.tracing import TraceSaver, start_trace, end_trace, get_trace_config
from src.tracing.trace_saver import (
    TraceConfig,
    _redact_secrets,
    _safe_serialize,
)


class TestTraceConfig:
    """Tests for TraceConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TraceConfig()
        assert config.enabled is True
        assert config.trace_dir == Path("./traces")
        assert config.max_chars == 5000

    def test_config_from_env(self):
        """Test loading config from environment."""
        with patch.dict(os.environ, {
            "TRACE_ENABLED": "0",
            "TRACE_DIR": "/tmp/custom_traces",
            "TRACE_MAX_CHARS": "1000",
        }):
            config = TraceConfig.from_env()
            assert config.enabled is False
            assert config.trace_dir == Path("/tmp/custom_traces")
            assert config.max_chars == 1000

    def test_config_enabled_variants(self):
        """Test various TRACE_ENABLED values."""
        for value, expected in [
            ("1", True),
            ("true", True),
            ("yes", True),
            ("TRUE", True),
            ("0", False),
            ("false", False),
            ("no", False),
        ]:
            with patch.dict(os.environ, {"TRACE_ENABLED": value}, clear=False):
                config = TraceConfig.from_env()
                assert config.enabled is expected, f"Failed for {value}"


class TestRedaction:
    """Tests for secret redaction."""

    def test_redact_api_key(self):
        """Test redacting API key fields."""
        data = {"api_key": "secret123", "name": "test"}
        result = _redact_secrets(data)
        assert result["api_key"] == "***"
        assert result["name"] == "test"

    def test_redact_nested(self):
        """Test redacting nested structures."""
        data = {
            "config": {
                "openrouter_api_key": "sk-123",
                "model": "gpt-4",
            },
            "authorization": "Bearer token",
        }
        result = _redact_secrets(data)
        assert result["config"]["openrouter_api_key"] == "***"
        assert result["config"]["model"] == "gpt-4"
        assert result["authorization"] == "***"

    def test_redact_list(self):
        """Test redacting lists."""
        data = [
            {"token": "abc123"},
            {"value": "safe"},
        ]
        result = _redact_secrets(data)
        assert result[0]["token"] == "***"
        assert result[1]["value"] == "safe"

    def test_redact_case_insensitive(self):
        """Test case-insensitive redaction."""
        data = {
            "API_KEY": "secret",
            "Token": "secret",
            "PASSWORD": "secret",
        }
        result = _redact_secrets(data)
        assert result["API_KEY"] == "***"
        assert result["Token"] == "***"
        assert result["PASSWORD"] == "***"


class TestSafeSerialization:
    """Tests for safe serialization."""

    def test_serialize_primitives(self):
        """Test serializing primitive types."""
        assert _safe_serialize(None) is None
        assert _safe_serialize("test") == "test"
        assert _safe_serialize(123) == 123
        assert _safe_serialize(1.5) == 1.5
        assert _safe_serialize(True) is True

    def test_serialize_dict(self):
        """Test serializing dictionaries."""
        data = {"key": "value", "nested": {"inner": 123}}
        result = _safe_serialize(data)
        assert result == data

    def test_serialize_list(self):
        """Test serializing lists."""
        data = [1, "two", {"three": 3}]
        result = _safe_serialize(data)
        assert result == data

    def test_truncate_long_string(self):
        """Test truncating long strings."""
        long_string = "x" * 10000
        result = _safe_serialize(long_string, max_chars=100)
        assert len(result) < len(long_string)
        assert "truncated" in result

    def test_serialize_unserializable(self):
        """Test serializing non-serializable objects."""
        class CustomClass:
            pass

        result = _safe_serialize(CustomClass())
        assert isinstance(result, str)


class TestTraceSaver:
    """Tests for TraceSaver callback handler."""

    def test_init_with_defaults(self):
        """Test TraceSaver initialization with defaults."""
        handler = TraceSaver()
        assert handler.run_id is not None
        assert len(handler.events) == 0
        assert handler.config.enabled is True

    def test_init_with_custom_run_id(self):
        """Test TraceSaver with custom run ID."""
        custom_id = "test-run-123"
        handler = TraceSaver(run_id=custom_id)
        assert handler.run_id == custom_id

    def test_add_event(self):
        """Test adding events manually."""
        handler = TraceSaver()
        handler._add_event(
            event_type="test",
            name="test_event",
            input_data={"key": "value"},
        )
        assert len(handler.events) == 1
        assert handler.events[0]["type"] == "test"
        assert handler.events[0]["name"] == "test_event"
        assert handler.events[0]["event_id"] == 0

    def test_event_id_increments(self):
        """Test that event IDs increment correctly."""
        handler = TraceSaver()
        handler._add_event(event_type="a", name="first")
        handler._add_event(event_type="b", name="second")
        handler._add_event(event_type="c", name="third")

        assert handler.events[0]["event_id"] == 0
        assert handler.events[1]["event_id"] == 1
        assert handler.events[2]["event_id"] == 2

    def test_disabled_handler_skips_events(self):
        """Test that disabled handler doesn't capture events."""
        config = TraceConfig(enabled=False)
        handler = TraceSaver(config=config)

        # Simulate LLM start callback
        handler.on_llm_start(
            serialized={"name": "gpt-4"},
            prompts=["Hello"],
            run_id=uuid4(),
        )

        assert len(handler.events) == 0

    def test_to_dict(self):
        """Test converting trace to dictionary."""
        handler = TraceSaver(run_id="test-123")
        handler._add_event(event_type="test", name="event1")

        result = handler.to_dict()

        assert result["run_id"] == "test-123"
        assert "start_time" in result
        assert "end_time" in result
        assert "duration_ms" in result
        assert result["total_events"] == 1
        assert len(result["events"]) == 1
        assert result["metadata"]["trace_version"] == "1.0"

    def test_save_creates_file(self):
        """Test saving trace to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(trace_dir=Path(tmpdir))
            handler = TraceSaver(run_id="test-save", config=config)
            handler._add_event(event_type="test", name="event1")

            saved_path = handler.save()

            assert saved_path.exists()
            assert "test-save" in saved_path.name

            # Verify content
            with open(saved_path) as f:
                data = json.load(f)
            assert data["run_id"] == "test-save"
            assert len(data["events"]) == 1

    def test_save_creates_directory(self):
        """Test that save creates trace directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_dir = Path(tmpdir) / "nested" / "traces"
            config = TraceConfig(trace_dir=trace_dir)
            handler = TraceSaver(config=config)

            saved_path = handler.save()

            assert trace_dir.exists()
            assert saved_path.exists()


class TestLLMCallbacks:
    """Tests for LLM callback methods."""

    def test_on_llm_start(self):
        """Test LLM start callback."""
        handler = TraceSaver()
        run_id = uuid4()

        handler.on_llm_start(
            serialized={"name": "gpt-4", "id": ["langchain", "llms", "openai"]},
            prompts=["What is 2+2?"],
            run_id=run_id,
        )

        assert len(handler.events) == 1
        assert handler.events[0]["type"] == "llm_start"
        assert handler.events[0]["name"] == "gpt-4"
        assert "What is 2+2?" in str(handler.events[0]["input"])

    def test_on_llm_end_calculates_latency(self):
        """Test LLM end callback calculates latency."""
        handler = TraceSaver()
        run_id = uuid4()

        # Start
        handler.on_llm_start(
            serialized={"name": "gpt-4"},
            prompts=["test"],
            run_id=run_id,
        )

        # Mock LLMResult
        mock_result = MagicMock()
        mock_result.generations = [[MagicMock(text="The answer is 4")]]
        mock_result.llm_output = {"token_usage": {"total_tokens": 50}}

        # End
        handler.on_llm_end(response=mock_result, run_id=run_id)

        assert len(handler.events) == 2
        assert handler.events[1]["type"] == "llm_end"
        assert "latency_ms" in handler.events[1]
        assert handler.events[1]["latency_ms"] >= 0


class TestToolCallbacks:
    """Tests for tool callback methods."""

    def test_on_tool_start(self):
        """Test tool start callback."""
        handler = TraceSaver()
        run_id = uuid4()

        handler.on_tool_start(
            serialized={"name": "calculator"},
            input_str="2 + 2",
            run_id=run_id,
        )

        assert len(handler.events) == 1
        assert handler.events[0]["type"] == "tool_start"
        assert handler.events[0]["name"] == "calculator"

    def test_on_tool_end(self):
        """Test tool end callback."""
        handler = TraceSaver()
        run_id = uuid4()

        # Start
        handler.on_tool_start(
            serialized={"name": "calculator"},
            input_str="2 + 2",
            run_id=run_id,
        )

        # End
        handler.on_tool_end(output="4", run_id=run_id)

        assert len(handler.events) == 2
        assert handler.events[1]["type"] == "tool_end"
        assert handler.events[1]["output"] == "4"

    def test_on_tool_error(self):
        """Test tool error callback."""
        handler = TraceSaver()
        run_id = uuid4()

        # Start
        handler.on_tool_start(
            serialized={"name": "bad_tool"},
            input_str="invalid",
            run_id=run_id,
        )

        # Error
        handler.on_tool_error(
            error=ValueError("Tool failed"),
            run_id=run_id,
        )

        assert len(handler.events) == 2
        assert handler.events[1]["type"] == "error"
        assert "Tool failed" in handler.events[1]["error"]


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_start_trace(self):
        """Test start_trace helper."""
        handler, run_id = start_trace()

        assert isinstance(handler, TraceSaver)
        assert handler.run_id == run_id
        assert len(run_id) > 0

    def test_start_trace_with_custom_id(self):
        """Test start_trace with custom run ID."""
        handler, run_id = start_trace(run_id="custom-123")

        assert run_id == "custom-123"
        assert handler.run_id == "custom-123"

    def test_end_trace_saves_file(self):
        """Test end_trace saves trace to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(trace_dir=Path(tmpdir))
            handler, run_id = start_trace(config=config)

            handler._add_event(event_type="test", name="event1")

            saved_path = end_trace(handler)

            assert saved_path is not None
            assert saved_path.exists()

    def test_end_trace_disabled_returns_none(self):
        """Test end_trace with disabled tracing returns None."""
        config = TraceConfig(enabled=False)
        handler, run_id = start_trace(config=config)

        result = end_trace(handler)

        assert result is None


class TestIntegration:
    """Integration tests for trace capture."""

    def test_full_trace_flow(self):
        """Test complete trace capture flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(trace_dir=Path(tmpdir))
            handler, run_id = start_trace(config=config)

            # Simulate LLM call
            llm_run_id = uuid4()
            handler.on_llm_start(
                serialized={"name": "gpt-4"},
                prompts=["Hello"],
                run_id=llm_run_id,
            )

            mock_result = MagicMock()
            mock_result.generations = [[MagicMock(text="Hi there!")]]
            mock_result.llm_output = {}

            handler.on_llm_end(response=mock_result, run_id=llm_run_id)

            # Simulate tool call
            tool_run_id = uuid4()
            handler.on_tool_start(
                serialized={"name": "search"},
                input_str="python docs",
                run_id=tool_run_id,
            )
            handler.on_tool_end(output="Found 10 results", run_id=tool_run_id)

            # Save trace
            saved_path = end_trace(handler)

            # Verify
            assert saved_path.exists()

            with open(saved_path) as f:
                data = json.load(f)

            assert data["run_id"] == run_id
            assert data["total_events"] == 4
            assert data["events"][0]["type"] == "llm_start"
            assert data["events"][1]["type"] == "llm_end"
            assert data["events"][2]["type"] == "tool_start"
            assert data["events"][3]["type"] == "tool_end"

    def test_trace_with_error(self):
        """Test trace captures errors correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(trace_dir=Path(tmpdir))
            handler, run_id = start_trace(config=config)

            # Add error event
            handler.add_error_event(
                ValueError("Something went wrong"),
                context="test_context",
            )

            saved_path = end_trace(handler)

            with open(saved_path) as f:
                data = json.load(f)

            assert len(data["events"]) == 1
            assert data["events"][0]["type"] == "error"
            assert "Something went wrong" in data["events"][0]["error"]

    def test_trace_redacts_secrets(self):
        """Test that secrets are redacted in saved traces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TraceConfig(trace_dir=Path(tmpdir))
            handler, run_id = start_trace(config=config)

            handler._add_event(
                event_type="test",
                name="test",
                input_data={"api_key": "secret123", "query": "safe"},
            )

            saved_path = end_trace(handler)

            with open(saved_path) as f:
                data = json.load(f)

            assert data["events"][0]["input"]["api_key"] == "***"
            assert data["events"][0]["input"]["query"] == "safe"
