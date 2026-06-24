"""Shared filesystem paths and run-artifact helpers for the web layer.

These were previously module-level globals in ``app.py``. Centralising them
keeps the route handlers thin and makes the directory layout discoverable in
one place.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..core.config import ROOT

# ── Runtime artifact directories ────────────────────────────────────────────
# Only true runtime artifacts (JSON, reports) go under sdlc_agent_output/
# Source code and tests are versioned at repo root
OUTPUT_ROOT = ROOT / "sdlc_agent_output"

RUNS_DIR = OUTPUT_ROOT / "runs"
REVIEW_DIR = OUTPUT_ROOT / "code_review"

# Versioned code and tests at repo root
SAMPLES_DIR = ROOT / "samples"
SRC_DIR = ROOT / "src"  # Generated production code (versioned)
TESTS_DIR = ROOT / "tests"  # Tests for generated application (versioned)
MANUAL_TESTS_DIR = TESTS_DIR / "manual"
AUTOMATION_SCRIPTS_DIR = TESTS_DIR / "automation"
UNIT_TESTS_DIR = TESTS_DIR / "unit"
RESULTS_DIR = TESTS_DIR / "results"


def _run_dir(run_id: str) -> Path:
    """Return (creating if needed) the artifact directory for a run."""
    p = RUNS_DIR / run_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_json(path: Path, model) -> None:
    """Serialise a Pydantic model to ``path`` as indented JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def _read_json(path: Path, model_cls):
    """Load and validate a Pydantic model of ``model_cls`` from ``path``."""
    return model_cls.model_validate_json(path.read_text(encoding="utf-8"))


def _new_run_id() -> str:
    """Generate a sortable, unique run identifier."""
    return "run-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6]
