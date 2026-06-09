"""End-to-end smoke test for the SDLC pipeline."""
from pathlib import Path

from sdlc_agent.orchestrator import Orchestrator
from sdlc_agent.stages import stage3_code, stage4_review


SAMPLES = Path(__file__).resolve().parents[1] / "samples"
SAMPLE = SAMPLES / "brd_payment_limits.md"
NATWEST_SAMPLE = SAMPLES / "brd_natwest_card_freeze.md"


def test_pipeline_runs_end_to_end_with_auto_approval() -> None:
    result = Orchestrator().run(str(SAMPLE), approval=lambda _b: True)

    assert result.brief.title == "Payment Limits Management"
    assert result.backlog.approved is True
    assert result.backlog.stories, "Stage 2 must produce at least one story"

    assert result.pull_request is not None
    assert result.pull_request.files, "Stage 3 must commit code files"

    assert result.review is not None
    assert result.review.verdict == "pass", result.review.findings

    assert result.tests is not None
    assert result.tests.files, "Stage 5 must add test files"
    assert result.tests.coverage_map, "Stage 5 must map tests to acceptance criteria"

    assert result.decision is not None
    assert result.decision.go is True, result.decision.blocking_reasons
    assert "Release note" in result.decision.release_note


def test_pipeline_halts_when_po_rejects() -> None:
    result = Orchestrator().run(str(SAMPLE), approval=lambda _b: False)
    assert result.backlog.approved is False
    assert result.pull_request is None
    assert result.decision is None


def test_natwest_card_freeze_brd_runs_clean() -> None:
    """NatWest reference BRD must produce a sign-off-ready backlog and reach GO."""
    result = Orchestrator().run(str(NATWEST_SAMPLE), approval=lambda _b: True)

    # Stage 1 — all six structured fields populated.
    brief = result.brief
    assert brief.title.startswith("Card Freeze")
    assert brief.business_goal
    assert brief.personas
    assert brief.functional_needs
    assert brief.non_functional_constraints
    assert brief.out_of_scope

    # Stage 2 — persona/need filtering removes nonsense pairings.
    backlog = result.backlog
    customer_freeze = [
        s for s in backlog.stories
        if "Retail customer" in s.persona and "freeze" in s.want.lower()
    ]
    assert customer_freeze, "Customer should have a freeze-card story"
    assert not any(
        "Compliance officer" in s.persona and s.want.lower().startswith("freeze")
        for s in backlog.stories
    ), "Compliance officer must not own the 'freeze a card' story"

    # ACs derived from constraints must mention the explicit numbers.
    all_acs = " ".join(ac for s in backlog.stories for ac in s.acceptance_criteria)
    assert "2s" in all_acs or "2seconds" in all_acs, all_acs
    assert "7 years" in all_acs

    # Stage 6 — GO.
    assert result.decision is not None
    assert result.decision.go is True, result.decision.blocking_reasons


def test_seeded_defect_is_caught_then_remediated() -> None:
    """Stage 4 must flag a deliberately faulty PR; remediation must clear it."""
    # First, confirm Stage 4 actually catches the seeded defect in isolation.
    from sdlc_agent.models import StoryBacklog, UserStory

    backlog = StoryBacklog(
        brief_title="Demo feature",
        stories=[UserStory(
            id="S-001", persona="Retail customer",
            want="do the thing", so_that="get value",
            acceptance_criteria=["AC-1"],
        )],
        approved=True,
    )
    faulty_pr = stage3_code.run(backlog, inject_defect=True)
    report = stage4_review.run(faulty_pr)
    high = [f for f in report.findings if f.severity.value in ("high", "critical")]
    assert high, "Stage 4 must flag the seeded HIGH-severity defects"
    assert any("TLS" in f.message for f in high), [f.message for f in high]
    assert report.verdict == "fail"

    # Now run the full pipeline with --inject-defect; remediation must clear it.
    result = Orchestrator().run(
        str(NATWEST_SAMPLE), approval=lambda _b: True, inject_defect=True,
    )
    assert result.decision is not None
    assert result.decision.go is True, result.decision.blocking_reasons
    # Final PR contents must not contain the seeded defect anymore.
    final_code = "\n".join(f.contents for f in result.pull_request.files)
    assert "verify=False" not in final_code
    assert "ghp_DEMO" not in final_code
