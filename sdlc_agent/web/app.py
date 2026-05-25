"""Flask web UI for the SDLC agent.

Each route corresponds to one button in the UI and one stage of the pipeline.
Run state is kept in a per-run JSON folder under `runs/<run-id>/` so the demo
is auditable and refresh-safe.
"""
from __future__ import annotations

# Load environment variables from .env file
from pathlib import Path as _Path
from dotenv import load_dotenv
import os as _os
_env_path = _Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
    # Verify it loaded
    if _os.getenv('GOOGLE_API_KEY'):
        print(f"[OK] Loaded GOOGLE_API_KEY from {_env_path}")
    else:
        print(f"[WARN] .env file exists but GOOGLE_API_KEY not found")
else:
    print(f"[WARN] .env file not found at {_env_path}")

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, render_template, request, send_from_directory

from ..models import PullRequest, ReviewReport, RequirementBrief, StoryBacklog, TestSuite
from ..stages import (
    stage1_requirement,
    stage2_stories,
    stage3_code,
    stage4_review,
    stage5_tests,
    stage6_deploy,
)
from ..testing_assets import write_manual_tests_xlsx, write_playwright_suite
from .stage5_new_handlers import (
    generate_manual_tests,
    generate_automation_scripts,
    execute_tests,
    heal_tests,
)


ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"
SAMPLES_DIR = ROOT / "samples"
SRC_DIR = ROOT / "src"
TESTING_DIR = ROOT / "Testing"
REVIEW_DIR = ROOT / "CodeReview"
MANUAL_TESTS_DIR = ROOT / "Manual_Test_Cases"
AUTOMATION_SCRIPTS_DIR = ROOT / "Automation_Scripts"
RESULTS_DIR = ROOT / "Results"


app = Flask(__name__, template_folder="templates", static_folder="static")

# Debug removed - app.py loaded successfully


@app.after_request
def add_no_cache_headers(response):
    """Disable caching for development to ensure fresh UI updates"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run_dir(run_id: str) -> Path:
    p = RUNS_DIR / run_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_json(path: Path, model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def _read_json(path: Path, model_cls):
    return model_cls.model_validate_json(path.read_text(encoding="utf-8"))


def _new_run_id() -> str:
    return "run-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6]


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    samples = sorted(p.name for p in SAMPLES_DIR.glob("*.md"))
    # Read template directly from disk to ensure fresh content
    from pathlib import Path
    template_path = Path(__file__).parent / "templates" / "index.html"
    template_content = template_path.read_text(encoding="utf-8")
    from flask import render_template_string
    return render_template_string(template_content, samples=samples)


# ---------------------------------------------------------------------------
# Stage 1 — Requirement ingestion
# ---------------------------------------------------------------------------
@app.post("/api/stage1")
def api_stage1():
    """Ingest a BRD picked from samples/ or uploaded inline as text."""
    try:
        payload = request.get_json(force=True)
        print(f"[Stage 1] Received payload: {payload}")

        run_id = payload.get("run_id") or _new_run_id()
        rd = _run_dir(run_id)
        print(f"[Stage 1] Run ID: {run_id}, Run dir: {rd}")

        if payload.get("brd_filename"):
            src = SAMPLES_DIR / payload["brd_filename"]
            print(f"[Stage 1] Looking for sample: {src}")
            if not src.exists():
                return jsonify({"error": f"Unknown sample: {src.name}"}), 400
            source_ref = str(src)
        elif payload.get("brd_text"):
            src = rd / "input_brd.md"
            src.write_text(payload["brd_text"], encoding="utf-8")
            source_ref = str(src)
            print(f"[Stage 1] Created BRD from text: {src}")
        else:
            return jsonify({"error": "Provide brd_filename or brd_text"}), 400

        print(f"[Stage 1] Running stage1_requirement.run({source_ref})")
        brief = stage1_requirement.run(source_ref)

        out = rd / "01_brief.json"
        _write_json(out, brief)
        print(f"[Stage 1] Success! Brief written to {out}")

        return jsonify({
            "run_id": run_id,
            "artifact": str(out.relative_to(ROOT)),
            "brief": brief.model_dump(),
        })
    except Exception as e:
        import traceback
        print(f"[Stage 1] ERROR: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Stage 1 failed: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# Stage 2 — User story generation
# ---------------------------------------------------------------------------
@app.post("/api/stage2")
def api_stage2():
    payload = request.get_json(force=True)
    run_id = payload["run_id"]
    rd = _run_dir(run_id)
    brief = _read_json(rd / "01_brief.json", RequirementBrief)
    backlog = stage2_stories.run(brief)
    out = rd / "02_backlog.json"
    _write_json(out, backlog)
    return jsonify({
        "run_id": run_id,
        "artifact": str(out.relative_to(ROOT)),
        "backlog": backlog.model_dump(),
        "generation_source": backlog.__dict__.get("_generation_source", "rules"),
        "generation_backend": backlog.__dict__.get("_generation_backend", "stub"),
    })


@app.post("/api/approve")
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
# Stage 3 — Code generation
# ---------------------------------------------------------------------------
@app.post("/api/stage3")
def api_stage3():
    payload = request.get_json(force=True)
    run_id = payload["run_id"]
    inject = bool(payload.get("inject_defect", False))
    rd = _run_dir(run_id)

    backlog = _read_json(rd / "02_backlog.json", StoryBacklog)
    if not backlog.approved:
        return jsonify({"error": "Backlog is not approved. Run /api/approve first."}), 400

    pr = stage3_code.run(backlog, inject_defect=inject)
    _write_json(rd / "03_pr.json", pr)

    # Materialise generated files to disk under src/.
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for f in pr.files:
        target = ROOT / f.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f.contents, encoding="utf-8")
        written.append(str(target.relative_to(ROOT)))

    return jsonify({
        "run_id": run_id,
        "pr": pr.model_dump(),
        "files_written": written,
        "inject_defect": inject,
        "generation_source": pr.__dict__.get("_generation_source", "rules"),
        "generation_backend": pr.__dict__.get("_generation_backend", "stub"),
    })


# ---------------------------------------------------------------------------
# Stage 4 — Code review
# ---------------------------------------------------------------------------
@app.post("/api/stage4")
def api_stage4():
    payload = request.get_json(force=True)
    run_id = payload["run_id"]
    rd = _run_dir(run_id)
    pr = _read_json(rd / "03_pr.json", PullRequest)
    report = stage4_review.run(pr)
    _write_json(rd / "04_review.json", report)

    # Mirror to the CodeReview folder requested by the brief.
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    review_copy = REVIEW_DIR / f"{run_id}_review.json"
    _write_json(review_copy, report)
    md = REVIEW_DIR / f"{run_id}_review.md"
    md.write_text(_review_to_markdown(report), encoding="utf-8")

    return jsonify({
        "run_id": run_id,
        "report": report.model_dump(),
        "stored": [
            str(review_copy.relative_to(ROOT)),
            str(md.relative_to(ROOT)),
        ],
        "review_source": report.__dict__.get("_review_source", "rules"),
        "review_backend": report.__dict__.get("_review_backend", "stub"),
    })


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
@app.post("/api/stage5")
def api_stage5():
    payload = request.get_json(force=True)
    run_id = payload["run_id"]
    rd = _run_dir(run_id)
    pr = _read_json(rd / "03_pr.json", PullRequest)
    backlog = _read_json(rd / "02_backlog.json", StoryBacklog)
    suite = stage5_tests.run(pr, backlog)
    _write_json(rd / "05_tests.json", suite)
    _write_json(rd / "03_pr.json", pr)  # PR now has tests attached

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
@app.post("/api/stage5/manual-tests")
def api_stage5_manual():
    """Generate manual test cases Excel"""
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]
        print(f"[Stage 5.1] Generating manual tests for {run_id}")

        result = generate_manual_tests(run_id, ROOT, MANUAL_TESTS_DIR)
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.post("/api/stage5/automation-scripts")
def api_stage5_automation():
    """Generate Playwright automation scripts"""
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]
        print(f"[Stage 5.2] Generating automation scripts for {run_id}")

        result = generate_automation_scripts(run_id, ROOT, AUTOMATION_SCRIPTS_DIR)
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.post("/api/stage5/execute-tests")
def api_stage5_execute():
    """Execute Playwright tests"""
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]
        print(f"[Stage 5.3] Executing tests for {run_id}")

        result = execute_tests(run_id, ROOT, AUTOMATION_SCRIPTS_DIR, RESULTS_DIR)
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.post("/api/stage5/heal-tests")
def api_stage5_heal():
    """Analyze failures and heal tests"""
    try:
        payload = request.get_json(force=True)
        run_id = payload["run_id"]
        print(f"[Stage 5.4] Healing tests for {run_id}")

        result = heal_tests(run_id, ROOT, AUTOMATION_SCRIPTS_DIR, RESULTS_DIR)
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Stage 6 — Deployment readiness
# ---------------------------------------------------------------------------
@app.post("/api/stage6")
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
    return jsonify({"run_id": run_id, "decision": decision.model_dump()})


# ---------------------------------------------------------------------------
# File serving for the "Open file" links in the UI
# ---------------------------------------------------------------------------
@app.get("/files/<path:relpath>")
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


def main() -> None:
    """Run the Flask dev server."""
    app.run(host="127.0.0.1", port=5002, debug=False)


if __name__ == "__main__":
    main()
