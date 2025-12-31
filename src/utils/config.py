"""
Configuration management for Agent Autopsy.

Handles environment variables, API keys, and default settings.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration."""

    # OpenRouter settings
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Model settings
    default_model: str = "meta-llama/llama-3.1-8b-instruct"
    fallback_model: str = "meta-llama/llama-3.1-8b-instruct:free"

    # Analysis settings
    max_retries: int = 3
    timeout_seconds: int = 120
    max_tokens: int = 4096

    # Pattern detection thresholds
    loop_threshold: int = 3
    context_overflow_threshold: int = 100000
    retry_window_seconds: int = 60  # Time window for retry storm detection

    # Embedding settings (for Phase 3)
    embedding_model: str = "all-MiniLM-L6-v2"

    # Logging
    log_level: str = "INFO"

    # Paths
    output_dir: Path = field(default_factory=lambda: Path("./reports"))

    # Tracing settings
    trace_enabled: bool = True
    trace_dir: Path = field(default_factory=lambda: Path("./traces"))
    trace_max_chars: int = 5000

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.openrouter_api_key:
            # Try to load from environment
            load_dotenv()
            self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")

        if not self.openrouter_api_key:
            print("Warning: OPENROUTER_API_KEY not set. LLM analysis will be unavailable.")

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        load_dotenv()

        return cls(
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            default_model=os.getenv("DEFAULT_MODEL", "meta-llama/llama-3.1-8b-instruct"),
            fallback_model=os.getenv("FALLBACK_MODEL", "meta-llama/llama-3.1-8b-instruct:free"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            trace_enabled=os.getenv("TRACE_ENABLED", "1").lower() in ("1", "true", "yes"),
            trace_dir=Path(os.getenv("TRACE_DIR", "./traces")),
            trace_max_chars=int(os.getenv("TRACE_MAX_CHARS", "5000")),
        )

    def get_model(self, override: str | None = None) -> str:
        """Get the model to use, with optional override."""
        if override:
            return override
        return self.default_model

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary (hiding sensitive values)."""
        return {
            "openrouter_base_url": self.openrouter_base_url,
            "default_model": self.default_model,
            "fallback_model": self.fallback_model,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "loop_threshold": self.loop_threshold,
            "log_level": self.log_level,
            "has_api_key": bool(self.openrouter_api_key),
            "trace_enabled": self.trace_enabled,
            "trace_dir": str(self.trace_dir),
            "trace_max_chars": self.trace_max_chars,
        }


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
