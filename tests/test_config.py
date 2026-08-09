"""Configuration parsing, redaction, and global-instance behavior."""

from __future__ import annotations

import pytest

from agent_autopsy.utils.config import Config, get_config, set_config


@pytest.fixture(autouse=True)
def _restore(monkeypatch: pytest.MonkeyPatch) -> None:
    set_config(Config.from_env())
    yield
    set_config(Config.from_env())


class TestFromEnv:
    def test_env_overrides_applied(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEFAULT_MODEL", "custom-model")
        monkeypatch.setenv("LLM_PROVIDER", "OpenAI")
        monkeypatch.setenv("TRACE_MAX_CHARS", "1234")
        monkeypatch.setenv("ANALYSIS_TOKEN_BUDGET", "9999")
        cfg = Config.from_env()
        assert cfg.default_model == "custom-model"
        assert cfg.llm_provider == "openai"
        assert cfg.trace_max_chars == 1234
        assert cfg.analysis_token_budget == 9999

    def test_boolean_env_flags(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SEMANTIC_DRIFT_ENABLED", "0")
        monkeypatch.setenv("AUTOPSY_NO_EMBEDDINGS", "yes")
        cfg = Config.from_env()
        assert cfg.semantic_drift_enabled is False
        assert cfg.skip_embeddings is True

    def test_defaults_when_env_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for var in [
            "DEFAULT_MODEL",
            "LLM_PROVIDER",
            "PROVIDER",
            "TRACE_MAX_CHARS",
            "ANALYSIS_TOKEN_BUDGET",
            "SEMANTIC_DRIFT_ENABLED",
            "AUTOPSY_NO_EMBEDDINGS",
        ]:
            monkeypatch.delenv(var, raising=False)
        cfg = Config.from_env()
        assert cfg.default_model == "meta-llama/llama-3.1-8b-instruct"
        assert cfg.llm_provider == "openrouter"
        assert cfg.trace_max_chars == 5000
        assert cfg.analysis_token_budget == 12000
        assert cfg.semantic_drift_enabled is True
        assert cfg.skip_embeddings is False


class TestSensitiveValues:
    def test_to_dict_never_exposes_api_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-should-not-leak")
        cfg = Config.from_env()
        dumped = cfg.to_dict()
        serialized = str(dumped)
        assert "sk-should-not-leak" not in serialized
        for key in ["openrouter_api_key", "openai_api_key", "ollama_base_url"]:
            assert key not in dumped
        assert dumped.get("has_api_key") is True


class TestGlobalInstance:
    def test_get_config_returns_singleton(self) -> None:
        assert get_config() is get_config()

    def test_set_config_replaces_instance(self) -> None:
        custom = Config()
        custom.default_model = "custom"
        set_config(custom)
        assert get_config() is custom
        assert get_config().default_model == "custom"


class TestModelSelection:
    def test_override_takes_precedence(self) -> None:
        cfg = Config()
        cfg.default_model = "default-model"
        assert cfg.get_model() == "default-model"
        assert cfg.get_model("override-model") == "override-model"
