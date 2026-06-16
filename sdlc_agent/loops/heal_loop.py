"""Stage 5 Execute → Heal → Execute loop."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from .base import BaseLoop, LoopResult

logger = logging.getLogger(__name__)


class HealLoop(BaseLoop):
    """Loops test execute → heal → execute until all tests pass."""

    def __init__(self, max_iterations: int = 3):
        super().__init__(max_iterations=max_iterations, name="HealLoop")

    def execute(self, run_id: str, execute_fn, heal_fn) -> LoopResult:
        """
        Execute test/heal loop.

        Args:
            run_id: Current run ID
            execute_fn: Callable that runs Stage 5 execute. Returns dict with 'failed' count.
            heal_fn: Callable that runs Stage 5 heal. Returns dict with 'fixes_applied'.

        Returns:
            LoopResult
        """
        start = time.time()
        history = []
        last_execute_result = None

        for iteration in range(1, self.max_iterations + 1):
            self._log_iteration(iteration, "executing tests")

            # Run tests
            execute_result = execute_fn(run_id)
            last_execute_result = execute_result
            failed_count = execute_result.get("failed", 0)
            passed_count = execute_result.get("passed", 0)
            total = execute_result.get("total_tests", 0)

            history.append({
                "iteration": iteration,
                "phase": "execute",
                "total": total,
                "passed": passed_count,
                "failed": failed_count,
            })

            if failed_count == 0:
                logger.info(f"[HealLoop] All tests PASS on iteration {iteration}")
                return LoopResult(
                    status="success",
                    iterations=iteration,
                    final_output=execute_result,
                    history=history,
                    ended_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=int((time.time() - start) * 1000),
                )

            # Tests failed - try to heal
            self._log_iteration(iteration, f"healing {failed_count} failures")
            heal_result = heal_fn(run_id)
            fixes_applied = heal_result.get("fixes_applied", 0)

            history.append({
                "iteration": iteration,
                "phase": "heal",
                "fixes_applied": fixes_applied,
                "auto_fixable": heal_result.get("auto_fixable", 0),
            })

            if fixes_applied == 0:
                logger.warning(f"[HealLoop] No fixes applied on iteration {iteration}, halting")
                return LoopResult(
                    status="halted",
                    iterations=iteration,
                    final_output=last_execute_result,
                    history=history,
                    ended_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=int((time.time() - start) * 1000),
                    error="No auto-fixes available; manual intervention needed",
                )

            logger.info(f"[HealLoop] Applied {fixes_applied} fixes, re-running tests")

        # Max iterations reached
        return LoopResult(
            status="max_iterations",
            iterations=self.max_iterations,
            final_output=last_execute_result,
            history=history,
            ended_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=int((time.time() - start) * 1000),
            error=f"Could not heal all failures after {self.max_iterations} iterations",
        )
