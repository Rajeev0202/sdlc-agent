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

# ── Runtime artifact directories (anchored at the repo root) ────────────────
RUNS_DIR = ROOT / "runs"
SAMPLES_DIR = ROOT / "samples"
SRC_DIR = ROOT / "src"
TESTING_DIR = ROOT / "Testing"
REVIEW_DIR = ROOT / "CodeReview"
MANUAL_TESTS_DIR = ROOT / "Manual_Test_Cases"
AUTOMATION_SCRIPTS_DIR = ROOT / "Automation_Scripts"
RESULTS_DIR = ROOT / "Results"


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
