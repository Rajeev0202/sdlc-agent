"""Autonomous end-to-end pipeline loop."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from .base import BaseLoop, LoopResult
from .remediation_loop import RemediationLoop
from .heal_loop import HealLoop

logger = logging.getLogger(__name__)


class AutonomousPipelineLoop(BaseLoop):
    """
    Autonomous orchestrator that runs the SDLC pipeline.

    Two phases:
    - Phase 1: Stages 1 → 2  (halts at PO approval gate)
    - Phase 2: Stages 3 → 4 (remediation loop) → 5.1 → 5.2 → 5.3/5.4 (heal loop) → 6
    """

    def __init__(self):
        super().__init__(max_iterations=1, name="AutonomousPipeline")
        self.remediation = RemediationLoop(max_iterations=2)
        self.heal = HealLoop(max_iterations=3)

    def execute(self, source: str, stage_fns: dict, auto_approve: bool = False, approver: str = "auto-pipeline") -> LoopResult:
        """Run Phase 1 (Stages 1-2) and optionally Phase 2 if auto_approve=True."""
        start = time.time()
        history = []
        run_id = None

        try:
            # ── Phase 1: Stage 1 (Ingest) ──
            self._log_iteration(1, "Stage 1: Ingesting requirements")
            s1_result = stage_fns["stage1"](source=source)
            run_id = s1_result.get("run_id")
            history.append({"stage": 1, "status": "complete", "run_id": run_id})

            # ── Phase 1: Stage 2 (Plan) ──
            self._log_iteration(1, "Stage 2: Generating user stories")
            s2_result = stage_fns["stage2"](run_id=run_id)
            history.append({
                "stage": 2,
                "status": "complete",
                "stories": s2_result.get("stories_count", 0),
            })

            # ── PO Approval Gate ──
            if not auto_approve:
                logger.info("[AutonomousPipeline] Halted at PO approval gate")
                return LoopResult(
                    status="awaiting_approval",
                    iterations=1,
                    final_output={"run_id": run_id, "halted_at": "po_gate"},
                    history=history,
                    ended_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=int((time.time() - start) * 1000),
                )

            # Auto-approve and continue to Phase 2
            self._log_iteration(1, "PO Gate: Auto-approving backlog")
            stage_fns["approve"](run_id=run_id, approver=approver)
            history.append({"stage": "approve", "status": "auto-approved"})

            return self._run_phase2(run_id, stage_fns, history, start)

        except Exception as e:
            logger.exception("[AutonomousPipeline] Phase 1 crashed")
            return LoopResult(
                status="failed",
                iterations=1,
                final_output={"run_id": run_id},
                history=history,
                ended_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=int((time.time() - start) * 1000),
                error=str(e),
            )

    def execute_phase2(self, run_id: str, stage_fns: dict) -> LoopResult:
        """Run Phase 2 (Stages 3-6) after manual PO approval."""
        start = time.time()
        history = [{"stage": "approve", "status": "manually-approved"}]
        return self._run_phase2(run_id, stage_fns, history, start)

    def _run_phase2(self, run_id: str, stage_fns: dict, history: list, start: float) -> LoopResult:
        """Internal: Execute Phase 2 stages with loops."""
        try:
            # ── Stage 3 → 4 with Remediation Loop ──
            self._log_iteration(1, "Stage 3+4: Build/Review with remediation loop")
            remediation_result = self.remediation.execute(
                run_id,
                stage3_fn=lambda rid, feedback=None: stage_fns["stage3"](run_id=rid),
                stage4_fn=lambda rid: stage_fns["stage4"](run_id=rid),
            )
            history.append({
                "stage": "3+4",
                "loop": "remediation",
                "status": remediation_result.status,
                "iterations": remediation_result.iterations,
            })

            if remediation_result.status != "success":
                logger.error("[AutonomousPipeline] Remediation loop failed")
                return LoopResult(
                    status="failed",
                    iterations=1,
                    final_output={"run_id": run_id, "failed_at": "remediation"},
                    history=history,
                    ended_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=int((time.time() - start) * 1000),
                    error="Stage 4 review failed after retries",
                )

            # ── Stage 5.1: Manual Tests ──
            self._log_iteration(1, "Stage 5.1: Generating manual test cases")
            s51 = stage_fns["stage5_manual"](run_id=run_id)
            history.append({"stage": "5.1", "test_cases": s51.get("total_test_cases", 0)})

            # ── Stage 5.2: Automation Scripts ──
            self._log_iteration(1, "Stage 5.2: Generating automation scripts")
            s52 = stage_fns["stage5_automation"](run_id=run_id)
            history.append({"stage": "5.2", "scripts": s52.get("total_scripts", 0)})

            # ── Stage 5.3 → 5.4 with Heal Loop ──
            self._log_iteration(1, "Stage 5.3+5.4: Execute/Heal with loop")
            heal_result = self.heal.execute(
                run_id,
                execute_fn=lambda rid: stage_fns["stage5_execute"](run_id=rid),
                heal_fn=lambda rid: stage_fns["stage5_heal"](run_id=rid),
            )
            history.append({
                "stage": "5.3+5.4",
                "loop": "heal",
                "status": heal_result.status,
                "iterations": heal_result.iterations,
            })

            # ── Stage 6: Deploy Decision ──
            self._log_iteration(1, "Stage 6: Deployment decision")
            s6_result = stage_fns["stage6"](run_id=run_id)
            decision = s6_result.get("decision", {})
            go = decision.get("go", False)
            history.append({
                "stage": 6,
                "decision": "GO" if go else "NO-GO",
                "gates": decision.get("gates", {}),
            })

            return LoopResult(
                status="success" if go else "completed_no_go",
                iterations=1,
                final_output={
                    "run_id": run_id,
                    "decision": decision,
                    "remediation_iterations": remediation_result.iterations,
                    "heal_iterations": heal_result.iterations,
                },
                history=history,
                ended_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=int((time.time() - start) * 1000),
            )

        except Exception as e:
            logger.exception("[AutonomousPipeline] Phase 2 crashed")
            return LoopResult(
                status="failed",
                iterations=1,
                final_output={"run_id": run_id},
                history=history,
                ended_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=int((time.time() - start) * 1000),
                error=str(e),
            )
