"""End-to-end SDLC agent — Phase 1 (Claude Code).

Orchestrates six specialist subagents to turn a business requirement into a
deployment-ready pull request, with exactly one human approval gate.

Harness integration: Provides observability, state management, hooks, and
lifecycle management directly within the Python agent.
"""

__version__ = "0.1.0"

# Auto-initialize harness when module is imported
from .harness import ensure_harness as _ensure_harness
_ensure_harness()

from .harness import (
    Harness,
    get_harness,
    reset_harness,
    Severity,
    TokenUsage,
    record_llm_usage,
)
from .harness import register_default_hooks

__all__ = [
    "Harness",
    "get_harness",
    "reset_harness",
    "register_default_hooks",
    "Severity",
    "TokenUsage",
    "record_llm_usage",
]
