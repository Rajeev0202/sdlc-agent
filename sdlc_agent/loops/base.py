"""Base class for all loops."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LoopResult:
    """Result of a loop execution."""

    status: str  # "success", "failed", "max_iterations", "halted"
    iterations: int
    final_output: Any = None
    history: list[dict] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: str = ""
    duration_ms: int = 0
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "iterations": self.iterations,
            "history": self.history,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class BaseLoop:
    """Base class for all loops."""

    def __init__(self, max_iterations: int = 3, name: str = "BaseLoop"):
        self.max_iterations = max_iterations
        self.name = name

    def execute(self, *args, **kwargs) -> LoopResult:
        """Execute the loop. Override in subclasses."""
        raise NotImplementedError

    def _log_iteration(self, iteration: int, status: str, details: dict | None = None):
        """Log iteration progress."""
        msg = f"[{self.name}] Iteration {iteration}: {status}"
        if details:
            msg += f" | {details}"
        logger.info(msg)
