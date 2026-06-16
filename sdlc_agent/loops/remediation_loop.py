"""Stage 3 ↔ Stage 4 remediation loop."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from .base import BaseLoop, LoopResult

logger = logging.getLogger(__name__)


class RemediationLoop(BaseLoop):
    """Loops Stage 3 (Build) and Stage 4 (Review) until review passes."""

    def __init__(self, max_iterations: int = 2):
        super().__init__(max_iterations=max_iterations, name="RemediationLoop")

    def execute(self, run_id: str, stage3_fn, stage4_fn) -> LoopResult:
        """
        Execute build/review remediation loop.

        Args:
            run_id: Current run ID
            stage3_fn: Callable that runs Stage 3 (build). Returns dict.
            stage4_fn: Callable that runs Stage 4 (review). Returns dict with 'verdict'.

        Returns:
            LoopResult with final status
        """
        start = time.time()
        history = []
        feedback = None

        for iteration in range(1, self.max_iterations + 2):  # +1 for first attempt
            self._log_iteration(iteration, "starting build")

            # Run Stage 3 (Build)
            build_result = stage3_fn(run_id, feedback=feedback)
            history.append({
                "iteration": iteration,
                "stage": 3,
                "result": "built",
                "files_count": len(build_result.get("files_written", [])),
            })

            self._log_iteration(iteration, "starting review")

            # Run Stage 4 (Review)
            review_result = stage4_fn(run_id)
            verdict = review_result.get("report", {}).get("verdict", "unknown")

            history.append({
                "iteration": iteration,
                "stage": 4,
                "verdict": verdict,
                "findings_count": len(review_result.get("report", {}).get("findings", [])),
            })

            if verdict == "pass":
                logger.info(f"[RemediationLoop] PASS on iteration {iteration}")
                return LoopResult(
                    status="success",
                    iterations=iteration,
                    final_output={"build": build_result, "review": review_result},
                    history=history,
                    ended_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=int((time.time() - start) * 1000),
                )

            # Capture findings for next iteration as feedback
            findings = review_result.get("report", {}).get("findings", [])
            high_critical = [
                f for f in findings
                if f.get("severity") in ("high", "critical")
                and not f.get("message", "").startswith("[LLM]")
            ]

            feedback = {
                "previous_verdict": verdict,
                "blocking_findings": high_critical[:5],  # Top 5 to keep prompt manageable
            }

            logger.warning(
                f"[RemediationLoop] FAIL on iteration {iteration} "
                f"({len(high_critical)} blocking findings). Retrying..."
            )

        # Exhausted retries
        logger.error(f"[RemediationLoop] Max iterations ({self.max_iterations + 1}) reached")
        return LoopResult(
            status="max_iterations",
            iterations=self.max_iterations + 1,
            final_output={"build": build_result, "review": review_result},
            history=history,
            ended_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=int((time.time() - start) * 1000),
            error="Review verdict failed after maximum retries",
        )
