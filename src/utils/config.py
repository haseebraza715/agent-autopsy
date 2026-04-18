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

    # LLM provider: openrouter | openai | anthropic | ollama
    llm_provider: str = "openrouter"
    openai_api_key: str = ""
    openai_api_base: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"

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
    model_context_limits_path: str = ""

    # Embedding settings (for Phase 3)
    embedding_model: str = "all-MiniLM-L6-v2"

    # Logging
    log_level: str = "INFO"

    # Analysis agent controls (Phase 2)
    analysis_max_iterations: int = 6
    analysis_max_report_revisions: int = 2
    analysis_report_quality_threshold: float = 0.65
    analysis_token_budget: int = 12000
    # Use Runnable.stream() inside graph LLM nodes (token deltas + LangGraph custom stream).
    analysis_use_llm_stream: bool = True
    semantic_drift_enabled: bool = True
    semantic_drift_model: str = "all-MiniLM-L6-v2"
    semantic_drift_delta_threshold: float = 0.35
    semantic_drift_low_threshold: float = 0.25

    # When True, never load sentence-transformers (CLI --no-embeddings or no goal on trace).
    skip_embeddings: bool = False

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

        if (self.llm_provider or "openrouter").lower() == "openrouter" and not self.openrouter_api_key:
            print("Warning: OPENROUTER_API_KEY not set. OpenRouter-backed LLM analysis will be unavailable.")

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
            model_context_limits_path=os.getenv("MODEL_CONTEXT_LIMITS_PATH", ""),
            trace_enabled=os.getenv("TRACE_ENABLED", "1").lower() in ("1", "true", "yes"),
            trace_dir=Path(os.getenv("TRACE_DIR", "./traces")),
            trace_max_chars=int(os.getenv("TRACE_MAX_CHARS", "5000")),
            analysis_max_iterations=int(os.getenv("ANALYSIS_MAX_ITERATIONS", "6")),
            analysis_max_report_revisions=int(os.getenv("ANALYSIS_MAX_REPORT_REVISIONS", "2")),
            analysis_report_quality_threshold=float(os.getenv("ANALYSIS_REPORT_QUALITY_THRESHOLD", "0.65")),
            analysis_token_budget=int(os.getenv("ANALYSIS_TOKEN_BUDGET", "12000")),
            analysis_use_llm_stream=os.getenv("ANALYSIS_USE_LLM_STREAM", "1").lower() in ("1", "true", "yes"),
            semantic_drift_enabled=os.getenv("SEMANTIC_DRIFT_ENABLED", "1").lower() in ("1", "true", "yes"),
            semantic_drift_model=os.getenv("SEMANTIC_DRIFT_MODEL", "all-MiniLM-L6-v2"),
            semantic_drift_delta_threshold=float(os.getenv("SEMANTIC_DRIFT_DELTA_THRESHOLD", "0.35")),
            semantic_drift_low_threshold=float(os.getenv("SEMANTIC_DRIFT_LOW_THRESHOLD", "0.25")),
            llm_provider=os.getenv("PROVIDER", os.getenv("LLM_PROVIDER", "openrouter")).strip().lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_api_base=os.getenv("OPENAI_API_BASE", ""),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            skip_embeddings=os.getenv("AUTOPSY_NO_EMBEDDINGS", "").lower() in ("1", "true", "yes"),
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
            "llm_provider": self.llm_provider,
            "default_model": self.default_model,
            "fallback_model": self.fallback_model,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "loop_threshold": self.loop_threshold,
            "context_overflow_threshold": self.context_overflow_threshold,
            "retry_window_seconds": self.retry_window_seconds,
            "model_context_limits_path": self.model_context_limits_path,
            "log_level": self.log_level,
            "analysis_max_iterations": self.analysis_max_iterations,
            "analysis_max_report_revisions": self.analysis_max_report_revisions,
            "analysis_report_quality_threshold": self.analysis_report_quality_threshold,
            "analysis_token_budget": self.analysis_token_budget,
            "analysis_use_llm_stream": self.analysis_use_llm_stream,
            "semantic_drift_enabled": self.semantic_drift_enabled,
            "semantic_drift_model": self.semantic_drift_model,
            "semantic_drift_delta_threshold": self.semantic_drift_delta_threshold,
            "semantic_drift_low_threshold": self.semantic_drift_low_threshold,
            "skip_embeddings": self.skip_embeddings,
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
