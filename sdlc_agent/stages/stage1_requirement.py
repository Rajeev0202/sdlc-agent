"""Stage 1 — Requirement ingestion.

Reads a BRD (Confluence page, file, or plain text) and produces a structured
`RequirementBrief`. Flags ambiguities as `open_questions` for the PO.

In production this calls Claude with a structured-output prompt. The mock here
applies simple heuristics so the pipeline runs offline.
"""
from __future__ import annotations

import re

from ..integrations import MockClaudeClient, MockConfluenceClient
from ..models import Persona, RequirementBrief


_PERSONA_PATTERNS = [
    (re.compile(r"\bcustomer(s)?\b", re.I), Persona(
        name="Retail customer",
        role="customer",
        goal="manage their account safely from the mobile app",
    )),
    (re.compile(r"\b(staff|agent|operator)s?\b", re.I), Persona(
        name="Call-centre agent",
        role="staff",
        goal="resolve customer queries within SLA",
    )),
    (re.compile(r"\b(compliance|risk|audit)\b", re.I), Persona(
        name="Compliance officer",
        role="compliance",
        goal="ensure changes meet regulatory obligations",
    )),
]

_AMBIGUITY_MARKERS = ("tbd", "tbc", "?", "as appropriate", "etc.")


def _extract_personas(text: str) -> list[Persona]:
    found: list[Persona] = []
    seen: set[str] = set()
    for pattern, persona in _PERSONA_PATTERNS:
        if pattern.search(text) and persona.name not in seen:
            found.append(persona)
            seen.add(persona.name)
    if not found:
        found.append(Persona(
            name="End user",
            role="user",
            goal="use the feature successfully",
        ))
    return found


def _extract_lines(text: str, marker: str) -> list[str]:
    out: list[str] = []
    capture = False
    for raw in text.splitlines():
        line = raw.strip()
        lower = line.lower().lstrip("# ").strip()
        if lower.startswith(marker):
            capture = True
            continue
        if capture:
            if line.startswith("#"):
                break
            if line.startswith(("- ", "* ")):
                out.append(line[2:].strip())
            elif not line:
                if out:
                    break
    return out


def _extract_open_questions(text: str) -> list[str]:
    questions: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if any(marker in lower for marker in _AMBIGUITY_MARKERS):
            questions.append(f"Clarify ambiguity in: '{line}'")
    return questions


def run(
    source_ref: str,
    *,
    confluence: MockConfluenceClient | None = None,
    claude: MockClaudeClient | None = None,
) -> RequirementBrief:
    """Ingest a requirement and return a structured brief."""
    confluence = confluence or MockConfluenceClient()
    claude = claude or MockClaudeClient()

    text = confluence.fetch_page(source_ref)
    claude.complete("stage1_ingest", {"chars": len(text)})

    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Untitled requirement"

    functional = _extract_lines(text, "functional") or [
        "Deliver the capability described in the BRD.",
    ]
    non_functional = _extract_lines(text, "non-functional") or [
        "Meet existing security and performance baselines.",
    ]
    out_of_scope = _extract_lines(text, "out of scope")
    goal_lines = _extract_lines(text, "business goal")
    business_goal = goal_lines[0] if goal_lines else (
        "Deliver business value aligned with the BRD."
    )

    return RequirementBrief(
        source=source_ref,
        title=title,
        business_goal=business_goal,
        personas=_extract_personas(text),
        functional_needs=functional,
        non_functional_constraints=non_functional,
        out_of_scope=out_of_scope,
        open_questions=_extract_open_questions(text),
    )
