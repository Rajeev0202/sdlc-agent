"""Stage 2 — User story generation.

Maps each (persona x functional need) pair into a concrete user story whose
language and acceptance criteria are specific enough that a Product Owner can
sign them off without material edits.
"""
from __future__ import annotations

import logging
import os
import re

from ..bootstrap import ensure_harness
from ..integrations import MockClaudeClient, MockJiraClient, JiraClient
from ..models import RequirementBrief, StoryBacklog, UserStory

logger = logging.getLogger(__name__)


_DEPENDENCY_HINTS = {
    "auth": "Authentication service (NatWest SSO)",
    "login": "Authentication service (NatWest SSO)",
    "sso": "Authentication service (NatWest SSO)",
    "balance": "Core banking API",
    "payment": "Payments rail",
    "limit": "Risk & limits service",
    "card": "Card management service",
    "freeze": "Card management service",
    "unfreeze": "Card management service",
    "audit": "Immutable audit log",
    "log": "Immutable audit log",
    "notification": "Notification service",
}

# Verb prefixes stripped from BRD bullets so the "I want ..." clause reads naturally.
_PRONOUN_PREFIXES = (
    "customer can ",
    "the customer can ",
    "compliance officer can ",
    "the compliance officer can ",
    "staff can ",
    "the staff can ",
    "user can ",
    "the user can ",
    "agent can ",
    "the agent can ",
)


def _clean_want(need: str) -> str:
    text = need.strip().rstrip(".")
    lower = text.lower()
    for prefix in _PRONOUN_PREFIXES:
        if lower.startswith(prefix):
            return text[len(prefix):]
    return text


def _persona_matches_need(persona_role: str, need: str) -> bool:
    """Drop persona/need pairs a real PO would never accept."""
    lower = need.lower()
    if persona_role == "compliance":
        return any(k in lower for k in ("audit", "log", "monitor", "report", "compliance"))
    if persona_role == "staff":
        return any(k in lower for k in ("resolve", "support", "call", "agent"))
    if persona_role in {"customer", "user"}:
        return not any(k in lower for k in ("audit", "compliance"))
    return True


def _derive_dependencies(need: str) -> list[str]:
    lower = need.lower()
    return sorted({label for key, label in _DEPENDENCY_HINTS.items() if key in lower})


def _criterion_from_constraint(constraint: str) -> str:
    c = constraint.strip().rstrip(".")
    lower = c.lower()
    latency = re.search(r"(\d+)\s*(ms|seconds?|s)\b[^.]*?p95", lower)
    if latency:
        return f"The endpoint responds within {latency.group(1)}{latency.group(2)} at p95 under nominal load."
    retention = re.search(r"(\d+)\s*years?", lower)
    if retention and any(k in lower for k in ("log", "retain", "audit", "immutab")):
        return f"All related events are persisted to the immutable audit log for {retention.group(1)} years."
    if "sso" in lower or "authentication" in lower:
        return "Requests are rejected unless the caller holds a valid NatWest SSO session token."
    if "tls" in lower:
        return "All inbound and outbound calls use TLS 1.2+ with certificate verification enabled."
    return f"The implementation satisfies the non-functional requirement: {c}."


def _derive_acceptance_criteria(
    want: str, constraints: list[str], goal: str
) -> list[str]:
    criteria: list[str] = [
        f"Given an authenticated user, when they {want.lower()}, then the request "
        "succeeds and a confirmation is returned.",
        f"Given an unauthenticated request, when {want.lower()} is attempted, "
        "then the request is rejected with HTTP 401 and no state changes.",
    ]
    criteria.extend(_criterion_from_constraint(c) for c in constraints)
    criteria.append(
        f"The delivered behaviour demonstrably contributes to the business goal: {goal}"
    )
    return criteria


def _generate_with_llm(
    brief: RequirementBrief, claude: MockClaudeClient
) -> list[UserStory] | None:
    """Ask Claude to produce stories. Returns None if LLM unavailable or invalid."""
    if not getattr(claude, "is_live", False):
        return None

    system = (
        "You are a senior NatWest business analyst. Convert a requirement brief "
        "into sign-off-ready Agile user stories. Each story must follow the "
        "'As a <persona>, I want <capability>, so that <benefit>' shape and "
        "include 3-6 testable acceptance criteria written in Given/When/Then "
        "where natural. Respect non-functional constraints (latency, audit, "
        "TLS, SSO) by reflecting them in ACs. Return STRICT JSON only."
    )
    schema_hint = (
        '{"stories": [ {"id": "S-001", "persona": "<persona name>", '
        '"want": "<capability>", "so_that": "<benefit>", '
        '"acceptance_criteria": ["..."], "dependencies": ["..."], '
        '"risks": ["..."]} ]}'
    )
    user = (
        f"Brief title: {brief.title}\n"
        f"Business goal: {brief.business_goal}\n\n"
        f"Personas:\n"
        + "\n".join(f"- {p.name} ({p.role}): {p.goal}" for p in brief.personas)
        + "\n\nFunctional needs:\n"
        + "\n".join(f"- {n}" for n in brief.functional_needs)
        + "\n\nNon-functional constraints:\n"
        + "\n".join(f"- {c}" for c in brief.non_functional_constraints)
        + "\n\nOut of scope:\n"
        + "\n".join(f"- {o}" for o in brief.out_of_scope)
        + "\n\nOpen questions:\n"
        + "\n".join(f"- {q}" for q in brief.open_questions)
        + "\n\nReturn JSON matching this shape exactly (no prose, no fences):\n"
        + schema_hint
    )

    data = claude.complete_json(system=system, user=user)
    if not isinstance(data, dict) or "stories" not in data:
        return None

    stories: list[UserStory] = []
    for idx, raw in enumerate(data["stories"], start=1):
        try:
            story = UserStory(
                id=str(raw.get("id") or f"S-{idx:03d}"),
                persona=str(raw["persona"]),
                want=str(raw["want"]),
                so_that=str(raw["so_that"]),
                acceptance_criteria=[str(c) for c in raw.get("acceptance_criteria", [])],
                dependencies=[str(d) for d in raw.get("dependencies", [])],
                risks=[str(r) for r in raw.get("risks", [])],
            )
        except (KeyError, TypeError, ValueError):
            return None
        if not story.acceptance_criteria:
            return None
        stories.append(story)

    return stories or None


def run(
    brief: RequirementBrief,
    *,
    jira: object = None,
    claude: MockClaudeClient | None = None,
) -> StoryBacklog:
    # Ensure harness is initialized (with hooks)
    ensure_harness()

    # Accept either MockJiraClient or JiraClient
    if jira is None:
        if all(os.environ.get(k) for k in ("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY")):
            jira = JiraClient(
                server_url=os.environ["JIRA_URL"],
                email=os.environ["JIRA_EMAIL"],
                api_token=os.environ["JIRA_API_TOKEN"],
                project_key=os.environ["JIRA_PROJECT_KEY"],
                auto_transition=os.environ.get("JIRA_AUTO_STATUS", "Ready for QA")  # Default to "Ready for QA"
            )
        else:
            jira = MockJiraClient()
    claude = claude or MockClaudeClient()
    claude.complete("stage2_stories", {"title": brief.title})

    backend = getattr(claude, "backend", "stub")
    logger.info("Stage 2 starting (backend=%s, is_live=%s)", backend, getattr(claude, "is_live", False))

    # Prefer live LLM output when available; fall back to deterministic rules.
    stories = _generate_with_llm(brief, claude)
    source = "llm" if stories is not None else "rules"
    if stories is None:
        logger.info("Stage 2 fell back to deterministic rule-based generation (backend=%s).", backend)
        stories = []
        counter = 0
        for persona in brief.personas:
            for need in brief.functional_needs:
                if not _persona_matches_need(persona.role, need):
                    continue
                counter += 1
                want = _clean_want(need)
                stories.append(
                    UserStory(
                        id=f"S-{counter:03d}",
                        persona=persona.name,
                        want=want,
                        so_that=persona.goal,
                        acceptance_criteria=_derive_acceptance_criteria(
                            want, brief.non_functional_constraints, brief.business_goal
                        ),
                        dependencies=_derive_dependencies(need),
                        risks=[f"Open question: {q}" for q in brief.open_questions],
                    )
                )
    else:
        logger.info("Stage 2 used LLM via %s (stories=%d).", backend, len(stories))

    for story in stories:
        jira.create_story(story)

    backlog = StoryBacklog(brief_title=brief.title, stories=stories)
    # Stash provenance on the model instance for the web layer (not persisted).
    backlog.__dict__["_generation_source"] = source
    backlog.__dict__["_generation_backend"] = backend
    return backlog
