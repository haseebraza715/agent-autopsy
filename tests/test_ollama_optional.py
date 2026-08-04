"""Ollama provider is first-class without requiring a running daemon."""

from agent_autopsy import api
from agent_autopsy.utils import config as cfgmod
from agent_autopsy.utils.config import Config


def test_ollama_provider_counts_as_configured() -> None:
    prev = cfgmod.get_config()
    try:
        c = Config.from_env()
        c.llm_provider = "ollama"
        cfgmod.set_config(c)
        assert api.llm_credentials_configured(c) is True
    finally:
        cfgmod.set_config(prev)
