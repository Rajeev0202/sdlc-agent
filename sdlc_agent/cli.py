"""Typer CLI for the SDLC agent.

Two entrypoint families:

* `run` / `stages` — full-pipeline mode used in tests and the standalone demo.
* `ingest` / `stories` / `code` / `review` / `tests` / `deploy` — per-stage
  commands invoked by Claude Code subagents. Each one reads/writes JSON
  artifacts under `runs/<run-id>/` so subagents can hand work off without
  re-parsing free text.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .integrations import (
    MockClaudeClient,
    MockGitHubClient,
)
from .models import (
    PullRequest,
    ReviewReport,
    RequirementBrief,
    StoryBacklog,
    TestSuite,
)
from .orchestrator import Orchestrator
from .stages import (
    stage1_requirement,
    stage2_stories,
    stage3_code,
    stage4_review,
    stage5_tests,
    stage6_deploy,
)


app = typer.Typer(add_completion=False, help="End-to-end SDLC agent (Phase 1).")
console = Console()


def _interactive_approval(backlog: StoryBacklog) -> bool:
    table = Table(title=f"Stories drafted for: {backlog.brief_title}")
    table.add_column("ID", style="cyan")
    table.add_column("Story")
    table.add_column("ACs", justify="right")
    for s in backlog.stories:
        table.add_row(s.id, s.as_a_statement, str(len(s.acceptance_criteria)))
    console.print(table)
    return typer.confirm("Approve backlog and proceed to code generation?", default=True)


@app.command()
def run(
    brd: Path = typer.Option(..., "--brd", exists=True, help="Path to a BRD markdown file."),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Skip the interactive PO approval prompt."
    ),
    output: Path | None = typer.Option(
        None, "--output", help="Write the full pipeline result as JSON to this path."
    ),
    inject_defect: bool = typer.Option(
        False, "--inject-defect",
        help="Demo aid: emit a faulty PR on the first Stage 3 pass so Stage 4 "
             "catches a seeded defect; the remediation rerun produces a clean PR.",
    ),
) -> None:
    """Run the full SDLC pipeline against a BRD file."""
    orchestrator = Orchestrator()
    approval = (lambda _b: True) if auto_approve else _interactive_approval
    result = orchestrator.run(str(brd), approval=approval, inject_defect=inject_defect)

    if result.decision is None:
        console.print(Panel.fit(
            "Backlog was not approved. Pipeline halted at the PO gate.",
            title="Halted", border_style="yellow",
        ))
        raise typer.Exit(code=1)

    decision = result.decision
    color = "green" if decision.go else "red"
    console.print(Panel.fit(
        ("GO — ready to deploy." if decision.go else "NO-GO — blocking gates:\n - "
         + "\n - ".join(decision.blocking_reasons)),
        title=f"Stage 6 verdict (PR #{decision.pr_number})",
        border_style=color,
    ))
    console.print(Panel(decision.release_note, title="Draft release note"))

    if output:
        output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"Full result written to [bold]{output}[/bold]")


@app.command()
def stages() -> None:
    """List the six pipeline stages."""
    names = [
        "1. Requirement ingestion",
        "2. User-story generation  (→ PO approval gate)",
        "3. Code generation",
        "4. Code review",
        "5. Test generation",
        "6. Deployment readiness",
    ]
    for n in names:
        console.print(f"  • {n}")


# ---------------------------------------------------------------------------
# Per-stage commands (used by Claude Code subagents)
# ---------------------------------------------------------------------------

def _write_json(path: Path, model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def _read_json(path: Path, model_cls):
    return model_cls.model_validate_json(path.read_text(encoding="utf-8"))


@app.command()
def ingest(
    brd: Path = typer.Option(..., "--brd", exists=True),
    output: Path = typer.Option(..., "--output"),
) -> None:
    """Stage 1 — produce a RequirementBrief JSON."""
    brief = stage1_requirement.run(str(brd))
    _write_json(output, brief)
    console.print(f"Stage 1 ✓ → {output}")


@app.command()
def stories(
    brief: Path = typer.Option(..., "--brief", exists=True),
    output: Path = typer.Option(..., "--output"),
) -> None:
    """Stage 2 — produce a StoryBacklog JSON (unapproved)."""
    b = _read_json(brief, RequirementBrief)
    backlog = stage2_stories.run(b)
    _write_json(output, backlog)
    console.print(f"Stage 2 ✓ → {output}  ({len(backlog.stories)} stories)")


@app.command()
def approve(
    backlog: Path = typer.Option(..., "--backlog", exists=True),
    approver: str = typer.Option("po@natwest", "--approver"),
) -> None:
    """Mark a backlog as PO-approved (records the approval gate clearance)."""
    b = _read_json(backlog, StoryBacklog)
    b.approved = True
    b.approver = approver
    b.approved_at = datetime.now(timezone.utc)
    _write_json(backlog, b)
    console.print(f"Backlog approved by {approver} → {backlog}")


@app.command()
def code(
    backlog: Path = typer.Option(..., "--backlog", exists=True),
    output: Path = typer.Option(..., "--output"),
    inject_defect: bool = typer.Option(
        False, "--inject-defect",
        help="Emit a deliberately faulty PR (demo aid for Stage 4).",
    ),
) -> None:
    """Stage 3 — generate code and emit a PullRequest JSON.

    Requires the backlog to be approved (Stage 2/3 gate).
    """
    b = _read_json(backlog, StoryBacklog)
    if not b.approved:
        raise typer.BadParameter("Backlog is not approved. Run `approve` first.")
    pr = stage3_code.run(
        b,
        github=MockGitHubClient(),
        claude=MockClaudeClient(),
        inject_defect=inject_defect,
    )
    _write_json(output, pr)
    console.print(f"Stage 3 ✓ → {output}  (PR #{pr.number}, {len(pr.files)} files)")


@app.command()
def review(
    pr: Path = typer.Option(..., "--pr", exists=True),
    output: Path = typer.Option(..., "--output"),
) -> None:
    """Stage 4 — review a PR and emit a ReviewReport JSON."""
    p = _read_json(pr, PullRequest)
    report = stage4_review.run(p)
    _write_json(output, report)
    color = "green" if report.verdict == "pass" else "red"
    console.print(
        f"[{color}]Stage 4 {report.verdict.upper()}[/{color}] → {output} "
        f"({len(report.findings)} findings)"
    )


@app.command()
def tests(
    pr: Path = typer.Option(..., "--pr", exists=True),
    backlog: Path = typer.Option(..., "--backlog", exists=True),
    output: Path = typer.Option(..., "--output"),
    pr_out: Path | None = typer.Option(
        None, "--pr-out", help="Optional path to write the updated PR JSON to."
    ),
) -> None:
    """Stage 5 — generate tests, attach to PR, emit TestSuite JSON."""
    p = _read_json(pr, PullRequest)
    b = _read_json(backlog, StoryBacklog)
    suite = stage5_tests.run(p, b)
    _write_json(output, suite)
    if pr_out is not None:
        _write_json(pr_out, p)
    console.print(f"Stage 5 ✓ → {output}  ({len(suite.files)} test files)")


@app.command()
def deploy(
    pr: Path = typer.Option(..., "--pr", exists=True),
    review: Path = typer.Option(..., "--review", exists=True),  # noqa: A002
    tests: Path = typer.Option(..., "--tests", exists=True),  # noqa: A002
    backlog: Path = typer.Option(..., "--backlog", exists=True),
    output: Path = typer.Option(..., "--output"),
) -> None:
    """Stage 6 — validate gates, draft release note, emit DeploymentDecision."""
    p = _read_json(pr, PullRequest)
    r = _read_json(review, ReviewReport)
    t = _read_json(tests, TestSuite)
    b = _read_json(backlog, StoryBacklog)
    decision = stage6_deploy.run(p, r, t, b)
    _write_json(output, decision)
    verdict = "GO" if decision.go else "NO-GO"
    color = "green" if decision.go else "red"
    console.print(f"[{color}]Stage 6 {verdict}[/{color}] → {output}")
    for reason in decision.blocking_reasons:
        console.print(f"  • {reason}")


if __name__ == "__main__":
    app()
