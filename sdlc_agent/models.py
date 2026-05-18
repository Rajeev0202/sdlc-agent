"""Pydantic data contracts passed between SDLC stages.

Each stage consumes the output of the previous one. Keeping these as explicit
typed models is what makes the pipeline auditable and platform-portable
(Phase 2 = Codex, Phase 3 = Nemotron + Codex + Claude).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Stage 1 — Requirement ingestion
# ---------------------------------------------------------------------------
class Persona(BaseModel):
    name: str
    role: str
    goal: str


class RequirementBrief(BaseModel):
    """Output of Stage 1. Consumed directly by Stage 2."""

    source: str = Field(description="Origin of the requirement (Confluence URL, BRD path, text).")
    title: str
    business_goal: str
    personas: list[Persona]
    functional_needs: list[str]
    non_functional_constraints: list[str]
    out_of_scope: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 2 — User story generation
# ---------------------------------------------------------------------------
class UserStory(BaseModel):
    id: str
    persona: str
    want: str
    so_that: str
    acceptance_criteria: list[str]
    dependencies: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    @property
    def as_a_statement(self) -> str:
        return f"As a {self.persona}, I want {self.want}, so that {self.so_that}."


class StoryBacklog(BaseModel):
    """Output of Stage 2. Held until the PO approval gate clears."""

    brief_title: str
    stories: list[UserStory]
    approved: bool = False
    approver: str | None = None
    approved_at: datetime | None = None


# ---------------------------------------------------------------------------
# Stage 3 — Code generation
# ---------------------------------------------------------------------------
class CodeFile(BaseModel):
    path: str
    language: str
    contents: str


class PullRequest(BaseModel):
    """Output of Stage 3 (draft PR). Mutated by Stages 4 and 5."""

    number: int
    branch: str
    title: str
    body: str
    files: list[CodeFile]
    story_ids: list[str]
    state: Literal["draft", "review", "approved", "ready"] = "draft"


# ---------------------------------------------------------------------------
# Stage 4 — Code review
# ---------------------------------------------------------------------------
class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewFinding(BaseModel):
    file: str
    line: int | None = None
    severity: Severity
    category: Literal[
        "security", "standards", "logic", "coverage", "compliance"
    ]
    message: str


class ReviewReport(BaseModel):
    """Output of Stage 4."""

    pr_number: int
    findings: list[ReviewFinding]
    verdict: Literal["pass", "fail"]

    @property
    def high_or_critical(self) -> list[ReviewFinding]:
        return [
            f for f in self.findings
            if f.severity in (Severity.HIGH, Severity.CRITICAL)
        ]


# ---------------------------------------------------------------------------
# Stage 5 — Test generation
# ---------------------------------------------------------------------------
class TestCoverage(BaseModel):
    acceptance_criterion: str
    test_names: list[str]


class TestSuite(BaseModel):
    """Output of Stage 5."""

    files: list[CodeFile]
    coverage_map: list[TestCoverage]


# ---------------------------------------------------------------------------
# Stage 6 — Deployment readiness
# ---------------------------------------------------------------------------
class DeploymentDecision(BaseModel):
    """Output of Stage 6 — final go/no-go."""

    pr_number: int
    go: bool
    gates: dict[str, bool]
    blocking_reasons: list[str] = Field(default_factory=list)
    release_note: str


# ---------------------------------------------------------------------------
# Top-level pipeline result
# ---------------------------------------------------------------------------
class PipelineResult(BaseModel):
    brief: RequirementBrief
    backlog: StoryBacklog
    pull_request: PullRequest | None = None
    review: ReviewReport | None = None
    tests: TestSuite | None = None
    decision: DeploymentDecision | None = None
