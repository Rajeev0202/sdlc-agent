"""Programmatic hooks for SDLC pipeline stages.

Replaces external JS hooks with Python-based event handlers that integrate
directly with the harness.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Harness


def on_stage_transition(harness: Harness, old_stage: str, new_stage: str, **kwargs) -> None:
    """Hook fired when pipeline transitions between stages."""
    from .core import Severity

    harness.log(
        Severity.INFO,
        f"Stage transition: {old_stage} → {new_stage}",
        tool="stage_transition",
    )

    # Update stage-specific metrics
    stage_data = harness.metrics.by_stage.setdefault(new_stage, {})
    stage_data["runs"] = stage_data.get("runs", 0) + 1
    harness._save_metrics()


def on_jira_card_created(harness: Harness, card_key: str, summary: str | None = None, **kwargs) -> None:
    """Hook fired when a Jira card is created."""
    from datetime import datetime, timezone
    from .core import Severity

    harness.log(
        Severity.INFO,
        f"Jira card created: {card_key}",
        tool="jira_create",
    )

    # Track in state
    harness.state.jira_creates.append({
        "key": card_key,
        "summary": summary,
        "parent": harness.state.epic.get("key") if harness.state.epic else None,
        "confluence_url": harness.state.source,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    harness._save_state()


def on_coverage_measured(harness: Harness, coverage_pct: float, **kwargs) -> None:
    """Hook fired when test coverage is measured."""
    from .core import Severity

    harness.state.coverage_pct = coverage_pct
    harness._save_state()

    if coverage_pct < harness.config.coverage_threshold:
        harness.log(
            Severity.WARN,
            f"Coverage below threshold: {coverage_pct}% < {harness.config.coverage_threshold}%",
            tool="coverage_check",
        )
    else:
        harness.log(
            Severity.INFO,
            f"Coverage gate passed: {coverage_pct}% ≥ {harness.config.coverage_threshold}%",
            tool="coverage_check",
        )


def on_git_push_attempt(harness: Harness, **kwargs) -> bool:
    """Hook fired before git push. Returns False to block the push."""
    from .core import Severity

    # Coverage gate
    if harness.state.coverage_pct is not None:
        if harness.state.coverage_pct < harness.config.coverage_threshold:
            harness.log(
                Severity.ERROR,
                f"PUSH BLOCKED: coverage {harness.state.coverage_pct}% < {harness.config.coverage_threshold}%",
                tool="git_push_gate",
            )
            return False

    return True


def on_requirements_ingested(harness: Harness, source: str, stories_found: int, open_questions: int, **kwargs) -> None:
    """Hook fired when requirements are ingested (Stage 1 - Brainstorming)."""
    from datetime import datetime, timezone
    from .core import Severity

    harness.log(
        Severity.INFO,
        f"Requirements ingested from {source}: {stories_found} stories, {open_questions} questions",
        tool="requirement_ingest",
    )

    # Track in state
    if not hasattr(harness.state, 'requirements_ingested'):
        harness.state.requirements_ingested = []

    harness.state.requirements_ingested.append({
        "source": source,
        "stories_found": stories_found,
        "open_questions": open_questions,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    harness._save_state()


def on_pr_created(harness: Harness, pr_number: int, branch: str, files_count: int, **kwargs) -> None:
    """Hook fired when a Pull Request is created (Stage 3)."""
    from datetime import datetime, timezone
    from .core import Severity

    harness.log(
        Severity.INFO,
        f"PR created: #{pr_number} on branch {branch} ({files_count} files)",
        tool="pr_create",
    )

    # Track in state
    if not hasattr(harness.state, 'prs_created'):
        harness.state.prs_created = []

    harness.state.prs_created.append({
        "pr_number": pr_number,
        "branch": branch,
        "files_count": files_count,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    harness._save_state()


def on_tests_generated(harness: Harness, test_files_count: int, coverage_map: list, **kwargs) -> None:
    """Hook fired when tests are generated (Stage 5)."""
    from datetime import datetime, timezone
    from .core import Severity

    harness.log(
        Severity.INFO,
        f"Tests generated: {test_files_count} test files created",
        tool="test_generation",
    )

    # Track in state
    if not hasattr(harness.state, 'test_generations'):
        harness.state.test_generations = []

    harness.state.test_generations.append({
        "test_files_count": test_files_count,
        "coverage_map_count": len(coverage_map) if coverage_map else 0,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    harness._save_state()


def register_default_hooks(harness: Harness) -> None:
    """Register all default SDLC hooks with the harness."""
    harness.register_hook("on_stage_transition", on_stage_transition)
    harness.register_hook("on_requirements_ingested", on_requirements_ingested)
    harness.register_hook("on_jira_card_created", on_jira_card_created)
    harness.register_hook("on_pr_created", on_pr_created)
    harness.register_hook("on_tests_generated", on_tests_generated)
    harness.register_hook("on_coverage_measured", on_coverage_measured)
    harness.register_hook("on_git_push_attempt", on_git_push_attempt)
