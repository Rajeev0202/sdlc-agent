"""Bootstrap module for automatic harness initialization.

This module ensures the harness is initialized and hooks are registered
when any SDLC agent code runs, regardless of how it's invoked:
- Via CLI
- Via web interface
- Via spawned agents
- Via skills
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def init_harness():
    """Initialize harness with hooks - safe to call multiple times."""
    try:
        from .core import get_harness

        # Get or create harness (hooks auto-register on first init)
        harness = get_harness()

        # Set run context if available
        if os.environ.get("SDLC_RUN_ID"):
            harness.state.trace_id = os.environ["SDLC_RUN_ID"]

        return harness
    except Exception as e:
        logger.warning(f"Harness initialization failed (non-fatal): {e}")
        return None


# Auto-initialize when module is imported
_harness = init_harness()


def ensure_harness():
    """Ensure harness is initialized - returns harness instance or None."""
    global _harness
    if _harness is None:
        _harness = init_harness()
    return _harness
