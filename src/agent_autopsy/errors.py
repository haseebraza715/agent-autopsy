"""Typed errors for Agent Autopsy (parse, plugins, LLM, schema)."""


class AutopsyError(Exception):
    """Base class for Agent Autopsy failures."""


class ParseError(AutopsyError):
    """Trace file or payload could not be parsed (JSON, format, or structure)."""


class SchemaValidationError(AutopsyError):
    """Normalized trace failed schema or contract validation."""


class PluginError(AutopsyError):
    """A plugin hook failed (parser, pattern detector, etc.)."""


class LLMError(AutopsyError):
    """LLM provider call failed after retries or exhausted the analysis budget."""
