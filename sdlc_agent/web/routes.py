"""HTTP routes for the SDLC Agent web UI.

Each route maps to one button in the UI and one stage of the pipeline. Run
state is persisted under ``runs/<run-id>/`` so the demo is auditable and
refresh-safe. The blueprint is registered by ``sdlc_agent.web.create_app``.
"""
from __future__ import annotations

import json
import logging
import os as _os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, render_template, request, send_from_directory

from ..core.config import ROOT
from ..core.models import (
    CodeFile,
    PullRequest,
    ReviewReport,
    RequirementBrief,
    StoryBacklog,
    TestCoverage,
    TestSuite,
)
from ..stages import (
    stage1_requirement,
    stage2_stories,
    stage3_code,
    stage4_review,
    stage5_tests,
    stage6_deploy,
)
from ..testing_assets import write_manual_tests_xlsx, write_playwright_suite
from ..skills.ingest_skill import IngestSkillAutomation
from ..skills.plan_skill import PlanSkillAutomation
from ..skills.build_skill import BuildSkillAutomation
from ..skills.review_skill import ReviewSkillAutomation
from ..skills.test_manual_skill import TestManualSkillAutomation
from ..skills.test_automation_skill import TestAutomationSkillAutomation
from ..skills.test_execute_skill import TestExecuteSkillAutomation
from ..skills.test_heal_skill import TestHealSkillAutomation
from ..loops import AutonomousPipelineLoop
from .stage5_new_handlers import (
    generate_manual_tests,
    generate_automation_scripts,
    execute_tests,
    heal_tests,
)
from .helpers import (
    AUTOMATION_SCRIPTS_DIR,
    MANUAL_TESTS_DIR,
    RESULTS_DIR,
    REVIEW_DIR,
    RUNS_DIR,
    SAMPLES_DIR,
    SRC_DIR,
    TESTING_DIR,
    _new_run_id,
    _read_json,
    _run_dir,
    _write_json,
)

logger = logging.getLogger(__name__)

bp = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
@bp.get("/")
def index():
    """Render the single-page SDLC pipeline UI."""
    samples = sorted(p.name for p in SAMPLES_DIR.glob("*.md"))
    return render_template("index.html", samples=samples)


@bp.post("/api/test")
def api_test():
    """Test endpoint to verify server is receiving requests"""
    payload = request.get_json(force=True)
    print(f"[TEST] Received: {payload}")
    return jsonify({"received": payload, "status": "ok"})


@bp.get("/api/version")
def api_version():
    """Version endpoint to verify which code is running"""
    return jsonify({
        "version": "2.0-confluence",
        "features": [
            "Confluence URL support",
            "Skill automation",
            "SDLC cycle visualization",
            "Cache-busting enabled"
        ],
        "endpoint": "/api/stage1",
        "expected_params": ["source", "run_id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


# ---------------------------------------------------------------------------
# Stage 1 — Requirement ingestion (integrated with /sdlc-ingest skill)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Autonomous Pipeline — runs all stages end-to-end with loops
# ---------------------------------------------------------------------------
@bp.post("/api/autonomous-pipeline")
def api_autonomous_pipeline():
    """Run the full SDLC pipeline autonomously with feedback loops.

    POST body: { "source": "<confluence-url-or-file-path>", "auto_approve": true }
    """
    try:
        payload = request.get_json(force=True)
        source = payload.get("source", "samples/brd_natwest_card_freeze.md")
        auto_approve = payload.get("auto_approve", True)

        print(f"[Autonomous Pipeline] Starting with source: {source}")

        # Build stage function dispatcher (uses Flask test client to call our own routes)
        client = current_app.test_client()

        def call_endpoint(path, payload):
            resp = client.post(path, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"{path} failed: {resp.get_json()}")
            return resp.get_json()

        stage_fns = {
            "stage1": lambda source: call_endpoint("/api/stage1", {"source": source}),
            "stage2": lambda run_id: call_endpoint("/api/stage2", {"run_id": run_id}),
            "approve": lambda run_id, approver: call_endpoint(
                "/api/approve", {"run_id": run_id, "approver": approver}
            ),
            "stage3": lambda run_id: call_endpoint(
                "/api/stage3", {"run_id": run_id, "inject_defect": False}
            ),
            "stage4": lambda run_id: call_endpoint("/api/stage4", {"run_id": run_id}),
            "stage5_manual": lambda run_id: call_endpoint(
                "/api/stage5/manual-tests", {"run_id": run_id}
            ),
            "stage5_automation": lambda run_id: call_endpoint(
                "/api/stage5/automation-scripts", {"run_id": run_id}
            ),
            "stage5_execute": lambda run_id: call_endpoint(
                "/api/stage5/execute-tests", {"run_id": run_id}
            ),
            "stage5_heal": lambda run_id: call_endpoint(
                "/api/stage5/heal-tests", {"run_id": run_id}
            ),
            "stage6": lambda run_id: call_endpoint("/api/stage6", {"run_id": run_id}),
        }

        # Run the autonomous loop
        pipeline = AutonomousPipelineLoop()
        result = pipeline.execute(
            source=source,
            stage_fns=stage_fns,
            auto_approve=auto_approve,
        )

        # Persist loop result for auditing
        run_id = result.final_output.get("run_id") if result.final_output else None
        brief_data = None
        backlog_data = None

        if run_id:
            rd = _run_dir(run_id)
            (rd / "autonomous_pipeline.json").write_text(
                json.dumps(result.to_dict(), indent=2),
                encoding="utf-8",
            )

            # Include brief and backlog data so UI can render Stage 1 & 2 panels
            brief_path = rd / "01_brief.json"
            backlog_path = rd / "02_backlog.json"
            if brief_path.exists():
                brief_data = json.loads(brief_path.read_text(encoding="utf-8"))
            if backlog_path.exists():
                backlog_data = json.loads(backlog_path.read_text(encoding="utf-8"))

        return jsonify({
            "status": result.status,
            "iterations": result.iterations,
            "duration_ms": result.duration_ms,
            "final_output": result.final_output,
            "history": result.history,
            "error": result.error,
            "brief": brief_data,
            "backlog": backlog_data,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.post("/api/autonomous-pipeline-resume")
def api_autonomous_pipeline_resume():
    """Resume autonomous pipeline at Phase 2 (Stages 3-6) after PO approval."""
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]

        print(f"[Autonomous Pipeline Resume] Phase 2 for {run_id}")

        client = current_app.test_client()

        def call_endpoint(path, payload):
            resp = client.post(path, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"{path} failed: {resp.get_json()}")
            return resp.get_json()

        stage_fns = {
            "stage3": lambda run_id: call_endpoint(
                "/api/stage3", {"run_id": run_id, "inject_defect": False}
            ),
            "stage4": lambda run_id: call_endpoint("/api/stage4", {"run_id": run_id}),
            "stage5_manual": lambda run_id: call_endpoint(
                "/api/stage5/manual-tests", {"run_id": run_id}
            ),
            "stage5_automation": lambda run_id: call_endpoint(
                "/api/stage5/automation-scripts", {"run_id": run_id}
            ),
            "stage5_execute": lambda run_id: call_endpoint(
                "/api/stage5/execute-tests", {"run_id": run_id}
            ),
            "stage5_heal": lambda run_id: call_endpoint(
                "/api/stage5/heal-tests", {"run_id": run_id}
            ),
            "stage6": lambda run_id: call_endpoint("/api/stage6", {"run_id": run_id}),
        }

        pipeline = AutonomousPipelineLoop()
        result = pipeline.execute_phase2(run_id, stage_fns)

        rd = _run_dir(run_id)
        (rd / "autonomous_pipeline_phase2.json").write_text(
            json.dumps(result.to_dict(), indent=2),
            encoding="utf-8",
        )

        return jsonify({
            "status": result.status,
            "iterations": result.iterations,
            "duration_ms": result.duration_ms,
            "final_output": result.final_output,
            "history": result.history,
            "error": result.error,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.post("/api/stage1")
def api_stage1():
    """Ingest requirements from Confluence URL, local file, or inline text.

    This endpoint automates the /sdlc-ingest skill logic.
    """
    try:
        payload = request.get_json(force=True)
        print(f"[Stage 1 - SKILL AUTOMATION] Received payload: {payload}")

        run_id = payload.get("run_id") or _new_run_id()
        rd = _run_dir(run_id)
        print(f"[Stage 1 - SKILL AUTOMATION] Run ID: {run_id}, Run dir: {rd}")

        # New unified input field
        source = payload.get("source", "").strip()

        # Legacy support for old payload format
        if not source:
            if payload.get("brd_filename"):
                source = payload["brd_filename"]
            elif payload.get("brd_text"):
                # Create temp file for inline text
                src = rd / "input_brd.md"
                src.write_text(payload["brd_text"], encoding="utf-8")
                source = str(src)
                print(f"[Stage 1 - SKILL AUTOMATION] Created BRD from text: {src}")

        if not source:
            return jsonify({"error": "Provide source URL or file path"}), 400

        # Initialize skill automation
        skill_automation = IngestSkillAutomation(ROOT)

        print(f"[Stage 1 - SKILL AUTOMATION] Running /sdlc-ingest skill automation on: {source}")

        # Run the automated skill
        try:
            skill_state = skill_automation.run(source)
            print(f"[Stage 1 - SKILL AUTOMATION] Skill completed successfully")
            skill_used = True
        except NotImplementedError as e:
            # Fall back to original implementation for unsupported sources
            print(f"[Stage 1 - SKILL AUTOMATION] Skill not supported for this source, falling back: {e}")
            return jsonify({"error": str(e)}), 501
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404

        # Convert skill state to RequirementBrief for compatibility
        brief = _skill_state_to_brief(skill_state)

        # Save in run directory for web UI tracking
        out = rd / "01_brief.json"
        _write_json(out, brief)
        print(f"[Stage 1 - SKILL AUTOMATION] Brief written to {out}")

        # Skill state is already saved to .claude/sdlc-state.json by the automation
        print(f"[Stage 1 - SKILL AUTOMATION] Skill state saved to .claude/sdlc-state.json")

        # Trigger harness hook for requirement ingestion
        try:
            from ..harness import get_harness
            harness = get_harness()
            harness._trigger_hook(
                "on_requirements_ingested",
                source=source,
                stories_found=len(skill_state.get("stories", [])),
                open_questions=len(skill_state.get("open_questions", []))
            )
        except Exception:
            pass  # Non-fatal

        return jsonify({
            "run_id": run_id,
            "artifact": str(out.relative_to(ROOT)),
            "brief": brief.model_dump(),
            "skill_used": skill_used,
            "skill_automation": True,
            "source_type": "confluence" if "confluence" in source.lower() else "file",
            "open_questions": skill_state.get("open_questions", []),
            "stories_found": len(skill_state.get("stories", [])),
            "acceptance_criteria_found": len(skill_state.get("acceptance_criteria", [])),
        })
    except Exception as e:
        import traceback
        print(f"[Stage 1 - SKILL AUTOMATION] ERROR: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Stage 1 skill automation failed: {str(e)}"}), 500


def _skill_state_to_brief(skill_state: dict) -> RequirementBrief:
    """Convert skill state format to RequirementBrief model."""
    from ..core.models import Persona

    # Extract personas from stories
    personas = []
    seen_personas = set()

    for story in skill_state.get("stories", []):
        persona_name = story.get("as_a", "").strip()
        if persona_name and persona_name not in seen_personas:
            personas.append(Persona(
                name=persona_name,
                role=persona_name,  # Use persona name as role
                goal=story.get("i_want", "").strip() or "Achieve business objectives"
            ))
            seen_personas.add(persona_name)

    # If no personas found, create a default one
    if not personas:
        personas = [Persona(
            name="User",
            role="End User",
            goal="Access and use the system effectively"
        )]

    # Build functional needs from stories
    functional_needs = []
    for story in skill_state.get("stories", []):
        need = story.get("i_want", "").strip()
        if need:
            functional_needs.append(need)

    # If no functional needs, use acceptance criteria
    if not functional_needs:
        functional_needs = skill_state.get("acceptance_criteria", [])[:3]  # Take first 3

    # Build brief
    brief = RequirementBrief(
        source=skill_state.get("source", ""),
        title=skill_state.get("epic", "Requirements"),
        business_goal=skill_state.get("epic", "Extracted from requirements document"),
        personas=personas,
        functional_needs=functional_needs,
        non_functional_constraints=skill_state.get("nfr", []),
        out_of_scope=skill_state.get("out_of_scope", []),
        open_questions=skill_state.get("open_questions", []),
    )

    return brief


# ---------------------------------------------------------------------------
# Stage 2 — User story generation (using /sdlc-plan skill automation)
# ---------------------------------------------------------------------------
@bp.post("/api/stage2")
def api_stage2():
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]
        jira_project_key = payload.get("jira_project_key", "SCRUM")

        rd = _run_dir(run_id)
        brief = _read_json(rd / "01_brief.json", RequirementBrief)

        print(f"[Stage 2] Generating user stories for {run_id} (skill automation)")

        # Use skill automation instead of old stage2_stories
        skill_automation = PlanSkillAutomation(ROOT)
        backlog = skill_automation.run(brief, jira_project_key)

        out = rd / "02_backlog.json"
        _write_json(out, backlog)

        # Get Jira links and mode
        jira_links = backlog.__dict__.get("_jira_links", {})

        # Persist jira_links separately so Stage 6 can transition them later
        if jira_links:
            (rd / "jira_links.json").write_text(
                json.dumps(jira_links, indent=2),
                encoding="utf-8",
            )
        jira_mode = type(skill_automation.jira).__name__
        jira_url = _os.environ.get("JIRA_URL", "")

        # Build clickable Jira URLs
        jira_issues = []
        for story_id, issue_key in jira_links.items():
            issue_url = f"{jira_url}/browse/{issue_key}" if jira_url and jira_mode == "JiraClient" else ""
            jira_issues.append({
                "story_id": story_id,
                "issue_key": issue_key,
                "url": issue_url,
            })

        return jsonify({
            "run_id": run_id,
            "artifact": str(out.relative_to(ROOT)),
            "backlog": backlog.model_dump(),
            "skill_automation": True,
            "stories_count": len(backlog.stories),
            "total_stories": len(backlog.stories),
            "jira_mode": jira_mode,
            "jira_url": jira_url,
            "jira_project_key": jira_project_key,
            "jira_issues": jira_issues,
            "generation_source": backlog.__dict__.get("_generation_source", "rules"),
            "generation_backend": backlog.__dict__.get("_generation_backend", "stub"),
            "generation_detail": backlog.__dict__.get("_generation_detail", ""),
        })
    except Exception as e:
        import traceback
        print(f"[Stage 2 - SKILL AUTOMATION] ERROR: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Stage 2 skill automation failed: {str(e)}"}), 500


@bp.post("/api/approve")
def api_approve():
    try:
        payload = request.get_json(force=True)
        run_id = payload.get("run_id")

        if not run_id:
            return jsonify({"error": "run_id is required"}), 400

        approver = payload.get("approver") or "po@natwest"
        rd = _run_dir(run_id)

        backlog_path = rd / "02_backlog.json"
        if not backlog_path.exists():
            return jsonify({"error": f"Backlog not found at {backlog_path}. Please run Stage 2 first."}), 404

        backlog = _read_json(backlog_path, StoryBacklog)
        backlog.approved = True
        backlog.approver = approver
        backlog.approved_at = datetime.now(timezone.utc)
        _write_json(backlog_path, backlog)

        return jsonify({"run_id": run_id, "approved": True, "approver": approver})

    except Exception as e:
        import traceback
        print(f"ERROR in /api/approve: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Stage 3 — Code generation (using /sdlc-build skill automation)
# ---------------------------------------------------------------------------
@bp.post("/api/stage3")
def api_stage3():
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]
        inject = bool(payload.get("inject_defect", False))
        rd = _run_dir(run_id)

        backlog = _read_json(rd / "02_backlog.json", StoryBacklog)
        if not backlog.approved:
            return jsonify({"error": "Backlog is not approved. Run /api/approve first."}), 400

        print(f"[Stage 3] Generating code for {run_id} (skill automation)")

        # Use skill automation instead of old stage3_code
        skill_automation = BuildSkillAutomation(ROOT)
        pr = skill_automation.run(backlog, inject_defect=inject)

        _write_json(rd / "03_pr.json", pr)

        # Trigger harness hook for PR creation
        try:
            from ..harness import get_harness
            harness = get_harness()
            harness._trigger_hook(
                "on_pr_created",
                pr_number=pr.number,
                branch=pr.branch,
                files_count=len(pr.files)
            )
        except Exception:
            pass  # Non-fatal
    except Exception as e:
        import traceback
        print(f"[Stage 3 - SKILL AUTOMATION] ERROR: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Stage 3 skill automation failed: {str(e)}"}), 500

    # Materialise generated files to disk under src/.
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for f in pr.files:
        target = ROOT / f.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f.contents, encoding="utf-8")
        written.append(str(target.relative_to(ROOT)))
        print(f"[Stage 3] Written: {f.path}")

    return jsonify({
        "run_id": run_id,
        "pr": pr.model_dump(),
        "skill_automation": True,
        "files_written": written,
        "files_generated": len(pr.files),
        "pr_number": pr.number,
        "pr_branch": pr.branch,
        "inject_defect": inject,
        "generation_source": pr.__dict__.get("_generation_source", "skill_automation"),
        "generation_backend": pr.__dict__.get("_generation_backend", "sdlc-build"),
    })


# ---------------------------------------------------------------------------
# Stage 4 — Code review (using /sdlc-review skill automation)
# ---------------------------------------------------------------------------
@bp.post("/api/stage4")
def api_stage4():
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]
        rd = _run_dir(run_id)
        pr = _read_json(rd / "03_pr.json", PullRequest)

        print(f"[Stage 4] Reviewing PR #{pr.number} for {run_id} (skill automation)")

        # Use skill automation instead of old stage4_review
        # Demo mode: Allows stub implementations to pass (ignores LLM findings)
        demo_mode = True  # Set to False for production-ready enforcement
        skill_automation = ReviewSkillAutomation(ROOT, demo_mode=demo_mode)
        print(f"[Stage 4] Demo mode: {demo_mode} (LLM findings will be {'ignored for verdict' if demo_mode else 'enforced'})")
        report = skill_automation.run(pr)

        _write_json(rd / "04_review.json", report)

        # Mirror to the CodeReview folder requested by the brief.
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        review_copy = REVIEW_DIR / f"{run_id}_review.json"
        _write_json(review_copy, report)
        md = REVIEW_DIR / f"{run_id}_review.md"
        md.write_text(_review_to_markdown(report), encoding="utf-8")

        # Determine actual review source for accurate badge
        llm_findings = sum(1 for f in report.findings if "[LLM]" in f.message)
        rule_findings = len(report.findings) - llm_findings
        review_source = "llm" if llm_findings > 0 else "rules"

        # If review passed, transition Jira cards to "Ready for QA"
        jira_transitions = []
        if report.verdict == "pass":
            jira_transitions = _transition_jira_cards(run_id, "Ready for QA")

        return jsonify({
            "run_id": run_id,
            "report": report.model_dump(),
            "skill_automation": True,
            "verdict": report.verdict,
            "findings_count": len(report.findings),
            "llm_findings": llm_findings,
            "rule_findings": rule_findings,
            "stored": [
                str(review_copy.relative_to(ROOT)),
                str(md.relative_to(ROOT)),
            ],
            "review_source": review_source,
            "review_backend": skill_automation.llm.backend,
            "jira_transitions": jira_transitions,
        })
    except Exception as e:
        import traceback
        print(f"[Stage 4 - SKILL AUTOMATION] ERROR: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Stage 4 skill automation failed: {str(e)}"}), 500


def _transition_jira_cards(run_id: str, target_status: str) -> list[dict]:
    """Generic helper: transition all Jira cards for a run to the target status."""
    transitions = []
    required = ("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY")
    if not all(_os.environ.get(k) for k in required):
        print(f"[Jira Transition] Credentials missing - skipping transition to '{target_status}'")
        return transitions

    try:
        from ..integrations.jira_client import JiraClient

        rd = _run_dir(run_id)
        jira_links_file = rd / "jira_links.json"
        if not jira_links_file.exists():
            print(f"[Jira Transition] No jira_links.json found in {run_id}")
            return transitions

        jira_links = json.loads(jira_links_file.read_text(encoding="utf-8"))
        if not jira_links:
            return transitions

        client = JiraClient(
            server_url=_os.environ["JIRA_URL"],
            email=_os.environ["JIRA_EMAIL"],
            api_token=_os.environ["JIRA_API_TOKEN"],
            project_key=_os.environ["JIRA_PROJECT_KEY"],
        )

        print(f"[Jira Transition] Moving {len(jira_links)} cards to '{target_status}'...")
        for story_id, issue_key in jira_links.items():
            success = client.transition_to_status(issue_key, target_status)
            transitions.append({
                "story_id": story_id,
                "issue_key": issue_key,
                "transitioned": success,
                "status": target_status if success else "failed",
            })
            print(f"[Jira Transition] {issue_key} ({story_id}): {'✓ ' + target_status if success else '✗ failed'}")

        return transitions
    except Exception as e:
        print(f"[Jira Transition] Failed: {e}")
        import traceback
        traceback.print_exc()
        return transitions


def _review_to_markdown(report: ReviewReport) -> str:
    lines = [
        f"# Code Review Report — PR #{report.pr_number}",
        "",
        f"**Verdict:** {report.verdict.upper()}",
        "",
        "| Severity | Category | File | Line | Message |",
        "|---|---|---|---|---|",
    ]
    for f in report.findings:
        lines.append(
            f"| {f.severity.value} | {f.category} | `{f.file}` | "
            f"{f.line or ''} | {f.message} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stage 5 — Test generation + execution
# ---------------------------------------------------------------------------
@bp.post("/api/stage5")
def api_stage5():
    payload = request.get_json(force=True)
    run_id = payload["run_id"]
    rd = _run_dir(run_id)
    pr = _read_json(rd / "03_pr.json", PullRequest)
    backlog = _read_json(rd / "02_backlog.json", StoryBacklog)
    suite = stage5_tests.run(pr, backlog)
    _write_json(rd / "05_tests.json", suite)
    _write_json(rd / "03_pr.json", pr)  # PR now has tests attached

    # Trigger harness hook for test generation
    try:
        from ..harness import get_harness
        harness = get_harness()
        harness._trigger_hook(
            "on_tests_generated",
            test_files_count=len(suite.files),
            coverage_map=suite.coverage_map
        )
    except Exception:
        pass  # Non-fatal

    # Materialise everything under a single Testing/ folder, per the brief.
    TESTING_DIR.mkdir(parents=True, exist_ok=True)
    automation_dir = TESTING_DIR / "automation"
    automation_dir.mkdir(exist_ok=True)
    for f in suite.files:
        target = automation_dir / Path(f.path).name
        target.write_text(f.contents, encoding="utf-8")
        # Also keep the canonical copy under tests/ so pytest picks it up.
        canon = ROOT / f.path
        canon.parent.mkdir(parents=True, exist_ok=True)
        canon.write_text(f.contents, encoding="utf-8")

    # 1. Manual test cases as Excel.
    xlsx_path = TESTING_DIR / f"{run_id}_manual_tests.xlsx"
    write_manual_tests_xlsx(backlog, xlsx_path)

    # 2. Playwright TypeScript suite under Testing/playwright/.
    playwright_dir = TESTING_DIR / "playwright"
    pw_info = write_playwright_suite(backlog, playwright_dir)

    # 3. Execute pytest for the deployment-readiness gate.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "--color=yes"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    result_path = TESTING_DIR / f"{run_id}_results.txt"
    result_path.write_text(
        proc.stdout + "\n--- STDERR ---\n" + proc.stderr, encoding="utf-8"
    )

    # 4. Execute the Playwright suite if Node + npx are available.
    playwright_result = _run_playwright(playwright_dir, run_id)

    return jsonify({
        "run_id": run_id,
        "suite": suite.model_dump(),
        "manual_tests_xlsx": str(xlsx_path.relative_to(ROOT)),
        "automation_dir": str(automation_dir.relative_to(ROOT)),
        "playwright_dir": str(playwright_dir.relative_to(ROOT)),
        "playwright_specs": [str(p.relative_to(ROOT)) for p in pw_info["specs"]],
        "playwright_result": playwright_result,
        "pytest_results_path": str(result_path.relative_to(ROOT)),
        "pytest_exit_code": proc.returncode,
        "pytest_tail": "\n".join((proc.stdout or "").splitlines()[-25:]),  # Show more lines
    })


def _run_playwright(playwright_dir: Path, run_id: str) -> dict:
    """Run `npx playwright test` if a Node toolchain is present.

    Always returns a dict describing what happened so the UI has something to
    render even when Playwright is not installed.
    """
    import shutil

    log_path = TESTING_DIR / f"{run_id}_playwright.log"
    npx = shutil.which("npx")
    if not npx:
        log_path.write_text(
            "npx not found on PATH. Install Node.js 18+ and run `npx playwright install`.\n",
            encoding="utf-8",
        )
        return {
            "executed": False,
            "reason": "npx not on PATH",
            "log_path": str(log_path.relative_to(ROOT)),
        }

    try:
        # `--reporter=list` is friendlier than the default for CI logs.
        proc = subprocess.run(
            [npx, "--yes", "playwright@1.47.0", "test", "--reporter=list"],
            cwd=str(playwright_dir),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        log_path.write_text(f"Playwright execution timed out: {exc}\n", encoding="utf-8")
        return {"executed": False, "reason": "timeout", "log_path": str(log_path.relative_to(ROOT))}

    log_path.write_text(
        (proc.stdout or "") + "\n--- STDERR ---\n" + (proc.stderr or ""),
        encoding="utf-8",
    )
    return {
        "executed": True,
        "exit_code": proc.returncode,
        "log_path": str(log_path.relative_to(ROOT)),
        "tail": "\n".join((proc.stdout or "").splitlines()[-20:]),
        "report_dir": str((playwright_dir / "playwright-report").relative_to(ROOT)),
    }


# ---------------------------------------------------------------------------
# Stage 5 — New 4-button workflow
# ---------------------------------------------------------------------------
@bp.post("/api/stage5/manual-tests")
def api_stage5_manual():
    """Generate manual test cases using /sdlc-test-manual skill automation"""
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]
        print(f"[Stage 5.1] Generating manual tests for {run_id} (skill automation)")

        # Load the backlog from this run
        rd = _run_dir(run_id)
        backlog = _read_json(rd / "02_backlog.json", StoryBacklog)

        # Populate sdlc-state.json with stories for the skill automation
        state_file = ROOT / ".claude" / "sdlc-state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing state or create new
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
        else:
            state = {}

        # Update with stories from backlog
        state["stories"] = [s.model_dump() for s in backlog.stories]
        state["total_stories"] = len(backlog.stories)

        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        print(f"[Stage 5.1] Populated sdlc-state.json with {len(backlog.stories)} stories")

        # Use skill automation with demo mode for fast generation
        demo_mode = True  # Set to False for LLM-powered test generation
        skill_automation = TestManualSkillAutomation(ROOT, demo_mode=demo_mode)
        print(f"[Stage 5.1] Demo mode: {demo_mode} (fast rule-based generation)")
        result = skill_automation.run(run_id)

        return jsonify({
            "run_id": run_id,
            "skill_automation": True,
            "total_test_cases": result.get("total_test_cases", 0),
            "output_dir": result.get("output_dir", f"runs/{run_id}/manual_test_cases"),
            "output_file": result.get("json_file", f"runs/{run_id}/manual_test_cases/manual_test_cases.json"),
            "excel_file": result.get("excel_file", f"runs/{run_id}/manual_test_cases/manual_test_cases.xlsx")
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.post("/api/stage5/automation-scripts")
def api_stage5_automation():
    """Generate Playwright automation scripts using /sdlc-test-automation skill automation"""
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]
        print(f"[Stage 5.2] Generating automation scripts for {run_id} (skill automation)")

        # Use skill automation with demo mode for fast generation
        demo_mode = True  # Set to False for LLM-powered script generation
        skill_automation = TestAutomationSkillAutomation(ROOT, demo_mode=demo_mode)
        print(f"[Stage 5.2] Demo mode: {demo_mode} (fast template-based generation)")
        result = skill_automation.run(run_id)

        return jsonify({
            "run_id": run_id,
            "skill_automation": True,
            "total_scripts": result.get("total_scripts", 0),
            "output_dir": result.get("output_dir", f"Testing/automation/{run_id}/"),
            "metadata_file": f"runs/{run_id}/automation_scripts.json"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.post("/api/stage5/execute-tests")
def api_stage5_execute():
    """Execute Playwright tests using /sdlc-test-execute skill automation"""
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]
        print(f"[Stage 5.3] Executing tests for {run_id} (skill automation)")

        # Use skill automation with demo mode for simulated execution
        demo_mode = True  # Set to False for real Playwright execution
        skill_automation = TestExecuteSkillAutomation(ROOT, demo_mode=demo_mode)
        print(f"[Stage 5.3] Demo mode: {demo_mode} (simulated test execution)")
        result = skill_automation.run(run_id)

        # Also save 05_tests.json for Stage 6 compatibility
        rd = _run_dir(run_id)
        playwright_dir = rd / "playwright_tests"

        # Build TestSuite from test execution results
        test_files = []
        if playwright_dir.exists():
            for test_file in playwright_dir.glob("*.spec.ts"):
                with open(test_file, 'r', encoding='utf-8') as f:
                    contents = f.read()
                test_files.append(CodeFile(
                    path=str(test_file.relative_to(ROOT)),
                    language="typescript",
                    contents=contents
                ))

        # Build coverage map from test results
        coverage_map = []
        test_results = result.get("results", [])

        # Group tests by story ID
        story_tests = {}
        for test_result in test_results:
            test_id = test_result.get("test_id", "unknown")

            # Extract story ID from test_id (e.g., "us-001.spec::test-1" -> "US-001")
            story_id = None
            test_id_lower = test_id.lower()
            if "us-" in test_id_lower:
                # Extract "us-001" from "us-001.spec::test-1"
                parts = test_id_lower.split("us-")
                if len(parts) > 1:
                    story_num = parts[1].split(".")[0].split("::")[0]
                    story_id = f"US-{story_num.upper()}"

            if story_id:
                if story_id not in story_tests:
                    story_tests[story_id] = []
                story_tests[story_id].append(test_id)

        # Create coverage map entries
        for story_id, test_names in story_tests.items():
            coverage_map.append(TestCoverage(
                acceptance_criterion=f"{story_id} acceptance criteria",
                test_names=test_names
            ))

        test_suite = TestSuite(files=test_files, coverage_map=coverage_map)
        _write_json(rd / "05_tests.json", test_suite)
        print(f"[Stage 5.3] Saved 05_tests.json with {len(test_files)} files")

        return jsonify({
            "run_id": run_id,
            "skill_automation": True,
            "total_tests": result.get("total_tests", 0),
            "passed": result.get("passed", 0),
            "failed": result.get("failed", 0),
            "pass_rate": result.get("pass_rate", 0),
            "output_file": f"runs/{run_id}/test_execution.json",
            "html_report": f"Testing/report/{run_id}/playwright_report.html"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.post("/api/stage5/heal-tests")
def api_stage5_heal():
    """Analyze failures and heal tests using /sdlc-test-heal skill automation"""
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]
        print(f"[Stage 5.4] Healing tests for {run_id} (skill automation)")

        # Use skill automation with demo mode for fast healing
        demo_mode = True  # Set to False for LLM-powered healing
        skill_automation = TestHealSkillAutomation(ROOT, demo_mode=demo_mode)
        print(f"[Stage 5.4] Demo mode: {demo_mode} (fast rule-based healing)")
        result = skill_automation.run(run_id)

        fixes_applied = result.get("fixes_applied", 0)
        print(f"[Stage 5.4] Applied {fixes_applied} automatic fixes")

        return jsonify({
            "run_id": run_id,
            "skill_automation": True,
            "failures_analyzed": result.get("failures_analyzed", 0),
            "auto_fixable": result.get("auto_fixable", 0),
            "manual_review_needed": result.get("manual_review_needed", 0),
            "fixes_applied": fixes_applied,
            "healing_suggestions": result.get("healing_suggestions", []),
            "output_file": f"runs/{run_id}/test_healing.json"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Stage 6 — Deployment readiness
# ---------------------------------------------------------------------------
@bp.post("/api/stage6")
def api_stage6():
    payload = request.get_json(force=True)
    run_id = payload["run_id"]
    rd = _run_dir(run_id)
    pr = _read_json(rd / "03_pr.json", PullRequest)
    review = _read_json(rd / "04_review.json", ReviewReport)
    tests = _read_json(rd / "05_tests.json", TestSuite)
    backlog = _read_json(rd / "02_backlog.json", StoryBacklog)
    decision = stage6_deploy.run(pr, review, tests, backlog)
    _write_json(rd / "06_decision.json", decision)
    (rd / "RELEASE_NOTES.md").write_text(decision.release_note, encoding="utf-8")

    # If deployment is GO, transition Jira cards to DONE
    jira_transitions = []
    if decision.go:
        target_status = _os.environ.get("JIRA_DONE_STATUS", "DONE")
        jira_transitions = _transition_jira_cards(run_id, target_status)

    return jsonify({
        "run_id": run_id,
        "decision": decision.model_dump(),
        "jira_transitions": jira_transitions,
    })


# ---------------------------------------------------------------------------
# File serving for the "Open file" links in the UI
# ---------------------------------------------------------------------------
@bp.get("/files/<path:relpath>")
def serve_artifact(relpath: str):
    safe = (ROOT / relpath).resolve()
    if ROOT not in safe.parents and safe != ROOT:
        return ("Forbidden", 403)
    if not safe.exists():
        return ("Not found", 404)
    if safe.is_dir():
        entries = sorted(safe.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        rows = "".join(
            f'<li><a href="/files/{(e.relative_to(ROOT).as_posix())}">{e.name}{"/" if e.is_dir() else ""}</a></li>'
            for e in entries
        )
        return (
            f"<!doctype html><meta charset=utf-8><title>{safe.name}</title>"
            f"<h2>{safe.relative_to(ROOT).as_posix()}/</h2><ul>{rows}</ul>",
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )
    return send_from_directory(str(safe.parent), safe.name, as_attachment=False)


@bp.get("/api/cost-stats")
def api_cost_stats():
    """Return LLM cost-saving statistics (cache hits, backend, etc.)."""
    from ..integrations.anthropic_client import get_cache_stats
    stats = get_cache_stats()

    hits = stats.get("hits", 0)
    misses = stats.get("misses", 0)
    total = hits + misses
    hit_rate = (hits / total * 100) if total else 0

    # Estimate savings: cache hit saves ~3000 tokens at $3/1M (Sonnet input)
    estimated_savings_usd = hits * 3000 * 3 / 1_000_000

    return jsonify({
        "cache_backend": stats.get("backend", "unknown"),
        "cache_size": stats.get("size", 0),
        "cache_ttl_seconds": stats.get("ttl_seconds", 0),
        "cache_hits": hits,
        "cache_misses": misses,
        "cache_writes": stats.get("writes", 0),
        "total_calls": total,
        "hit_rate_pct": round(hit_rate, 1),
        "estimated_savings_usd": round(estimated_savings_usd, 4),
        "batch_mode_enabled": _os.environ.get("STAGE3_BATCH_MODE", "1") == "1",
        "redis_configured": bool(_os.environ.get("REDIS_URL")),
    })


@bp.post("/api/cost-stats/clear")
def api_cost_stats_clear():
    """Clear the LLM response cache (useful for testing)."""
    from ..integrations.llm_cache import get_cache
    get_cache().clear()
    return jsonify({"status": "cleared"})
# ---------------------------------------------------------------------------
# Harness Verification Endpoints
# ---------------------------------------------------------------------------

def _harness_status_endpoint():
    """Check if harness is initialized with hooks (for verification)."""
    from ..harness import get_harness

    harness = get_harness()
    return jsonify({
        "initialized": True,
        "hooks_registered": harness._hooks_registered,
        "hook_events": list(harness._hooks.keys()),
        "hook_counts": {
            event: len(callbacks)
            for event, callbacks in harness._hooks.items()
        },
        "state": {
            "stage": harness.state.stage,
            "trace_id": harness.state.trace_id,
            "jira_cards_tracked": len(harness.state.jira_creates),
            "coverage_pct": harness.state.coverage_pct,
        },
        "config": {
            "coverage_threshold": harness.config.coverage_threshold,
            "enable_observability": harness.config.enable_observability,
            "enable_hooks": harness.config.enable_hooks,
        }
    })

bp.add_url_rule("/api/harness/status", "harness_status", _harness_status_endpoint, methods=["GET"])


def _test_jira_hook_endpoint():
    """Test endpoint to verify Jira hook fires in web context."""
    from ..integrations.jira_client import MockJiraClient
    from ..core.models import UserStory
    from ..harness import get_harness

    harness = get_harness()
    harness.state.epic = {"key": "WEB-TEST", "summary": "Web Hook Test"}

    jira = MockJiraClient()
    story = UserStory(
        id="S-WEB-TEST",
        persona="Web Tester",
        want="verify hooks work via uvicorn",
        so_that="ensure web deployment is correct",
        acceptance_criteria=[
            "Hooks are registered on uvicorn start",
            "Hooks fire when Jira cards are created",
            "State is tracked correctly"
        ]
    )

    initial_count = len(harness.state.jira_creates)
    issue_key = jira.create_story(story)
    hook_fired = len(harness.state.jira_creates) > initial_count

    return jsonify({
        "success": True,
        "hook_fired": hook_fired,
        "card_created": issue_key,
        "cards_before": initial_count,
        "cards_after": len(harness.state.jira_creates),
        "latest_card": harness.state.jira_creates[-1] if harness.state.jira_creates else None
    })

bp.add_url_rule("/api/test/jira-hook", "test_jira_hook", _test_jira_hook_endpoint, methods=["GET", "POST"])


