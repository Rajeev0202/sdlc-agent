"""
Automated implementation of /sdlc-plan skill for UI integration.

This module implements the logic from .claude/skills/sdlc-plan/SKILL.md
for creating Jira user story cards from requirements using Claude LLM.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..integrations.anthropic_client import MockClaudeClient
from ..core.models import RequirementBrief, StoryBacklog, UserStory

logger = logging.getLogger(__name__)


class PlanSkillAutomation:
    """Automates the /sdlc-plan skill logic with LLM-powered story decomposition."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.state_file = root_dir / ".claude" / "sdlc-state.json"
        self.llm = MockClaudeClient()
        self.jira = self._init_jira_client()
        logger.info(f"PlanSkillAutomation initialized with backend: {self.llm.backend}")
        logger.info(f"Jira client: {type(self.jira).__name__}")

    def _init_jira_client(self):
        """Initialize Jira client (real if configured, mock otherwise)."""
        from ..integrations import JiraClient, MockJiraClient

        required = ("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY")
        if all(os.environ.get(k) for k in required):
            try:
                return JiraClient(
                    server_url=os.environ["JIRA_URL"],
                    email=os.environ["JIRA_EMAIL"],
                    api_token=os.environ["JIRA_API_TOKEN"],
                    project_key=os.environ["JIRA_PROJECT_KEY"],
                    auto_transition=os.environ.get("JIRA_AUTO_STATUS"),
                )
            except Exception as e:
                logger.warning(f"Failed to initialize real Jira client: {e}. Falling back to mock.")
                return MockJiraClient(project_key=os.environ.get("JIRA_PROJECT_KEY", "SCRUM"))
        else:
            missing = [k for k in required if not os.environ.get(k)]
            logger.info(f"Jira credentials missing ({missing}), using MockJiraClient")
            return MockJiraClient()

    def run(self, brief: RequirementBrief, jira_project_key: str = "SCRUM") -> StoryBacklog:
        """
        Execute the /sdlc-plan skill logic.

        Args:
            brief: The requirement brief from Stage 1
            jira_project_key: Jira project key for creating issues

        Returns:
            StoryBacklog with generated user stories
        """
        # Step 1: Load requirements from state file
        requirements = self._load_requirements()

        # Step 2: Decompose into user stories
        stories = self._decompose_to_stories(requirements, brief)

        # Step 3: Create Jira cards (optional - requires Jira integration)
        jira_links = self._create_jira_cards(stories, jira_project_key)

        # Step 4: Build StoryBacklog
        backlog = self._create_backlog(brief, stories, jira_links)

        # Step 5: Update state file
        self._update_state(backlog)

        logger.info(f"Generated {len(stories)} user stories from requirements")

        return backlog

    def _load_requirements(self) -> list[dict[str, Any]]:
        """Load requirements from state file."""
        if not self.state_file.exists():
            return []

        with open(self.state_file, "r", encoding="utf-8") as f:
            state = json.load(f)

        return state.get("stories", [])

    def _decompose_to_stories(
        self, requirements: list[dict[str, Any]], brief: RequirementBrief
    ) -> list[UserStory]:
        """Decompose requirements into user stories using LLM intelligence."""
        # Track which path was taken for UI badge
        self._generation_path = "rules"  # default
        self._generation_detail = ""

        print(f"[Stage 2 - LLM Check] Backend: {self.llm.backend}", flush=True)
        print(f"[Stage 2 - LLM Check] is_live: {self.llm.is_live}", flush=True)
        print(f"[Stage 2 - LLM Check] Input requirements: {len(requirements)}", flush=True)

        # Try LLM-based decomposition first
        if self.llm.is_live:
            print("[Stage 2 - LLM Check] Attempting LLM decomposition via Claude...", flush=True)
            llm_stories = self._llm_decompose(requirements, brief)

            if llm_stories:
                self._generation_path = "llm"
                self._generation_detail = (
                    f"Claude LLM decomposed {len(requirements)} requirements "
                    f"into {len(llm_stories)} stories"
                )
                print(f"[Stage 2 - LLM Check] SUCCESS: {self._generation_detail}", flush=True)
                logger.info(self._generation_detail)
                return llm_stories
            else:
                self._generation_detail = "LLM returned no stories - fell back to rules"
                print(f"[Stage 2 - LLM Check] FALLBACK: {self._generation_detail}", flush=True)
                logger.warning(self._generation_detail)
        else:
            self._generation_detail = f"LLM not available (backend={self.llm.backend})"
            print(f"[Stage 2 - LLM Check] NO LLM: {self._generation_detail}", flush=True)

        # Fallback: rule-based decomposition
        rule_stories = self._rule_based_decompose(requirements, brief)
        if not self._generation_detail:
            self._generation_detail = f"Rule-based generated {len(rule_stories)} stories"
        return rule_stories

    def _llm_decompose(
        self, requirements: list[dict[str, Any]], brief: RequirementBrief
    ) -> list[UserStory]:
        """Use Claude LLM to intelligently decompose requirements into stories."""
        system_prompt = """You are an expert Agile coach decomposing requirements into user stories.

Apply the INVEST principle:
- Independent: Each story can be developed/tested separately
- Negotiable: Stories are not contracts, they're conversations
- Valuable: Each delivers value to users
- Estimable: Can be reasonably sized
- Small: Fits in a sprint (1-8 story points)
- Testable: Has clear acceptance criteria

Decomposition rules:
1. Split by microservice/module (one story per service)
2. Split by layer (API and UI as separate stories)
3. Split by integration boundary (external systems)
4. Split by user journey step (preconditions, main action, edge cases)

For each story, estimate story points using Fibonacci (1, 2, 3, 5, 8) based on:
- Complexity (algorithm difficulty)
- Effort (lines of code, tests needed)
- Risk (unknowns, dependencies)
- Doubt (unclear requirements)

Return ONLY valid JSON object with this structure (no markdown, no prose):
{
  "stories": [
    {
      "persona": "Card holder",
      "want": "freeze my card via mobile app",
      "so_that": "I can prevent fraud immediately",
      "acceptance_criteria": [
        "Given an authenticated card holder, when they request to freeze their card, then the card status is updated to FROZEN within 2 seconds",
        "Given an unauthenticated request, when freeze is attempted, then the request is rejected with HTTP 401"
      ],
      "dependencies": ["Card Management Service"],
      "risks": ["External API latency"]
    }
  ]
}"""

        # Format requirements as input
        req_text = "\n\n".join([
            f"Requirement {i+1}:\n"
            f"As a: {r.get('as_a', 'User')}\n"
            f"I want: {r.get('i_want', '')}\n"
            f"So that: {r.get('so_that', '')}\n"
            f"Acceptance Criteria:\n" + "\n".join(f"- {ac}" for ac in r.get('acceptance_criteria', []))
            for i, r in enumerate(requirements)
        ])

        user_prompt = f"""Project: {brief.title}
Business Goal: {brief.business_goal}

Non-Functional Requirements:
{chr(10).join(f"- {nfr}" for nfr in brief.non_functional_constraints)}

Personas:
{chr(10).join(f"- {p.name} ({p.role}): {p.goal}" for p in brief.personas)}

Requirements to decompose:
{req_text}

Decompose these requirements into well-defined user stories following INVEST principles.
Split by service, layer, and user journey where appropriate.

Return ONLY a JSON object with a "stories" array. No markdown fences, no explanatory text."""

        try:
            result = self.llm.complete_json(
                system=system_prompt, user=user_prompt, max_tokens=4096, temperature=0.3
            )

            # Handle both list and dict responses
            story_list = []
            if isinstance(result, list):
                story_list = result
            elif isinstance(result, dict) and "stories" in result:
                story_list = result["stories"]
            else:
                logger.warning(f"LLM returned unexpected format: {type(result)}")
                return []

            if not story_list:
                logger.warning("LLM returned empty story list")
                return []

            print(f"[Stage 2 - LLM] Received {len(story_list)} stories from LLM", flush=True)

            stories = []
            for i, s in enumerate(story_list, 1):
                if not isinstance(s, dict):
                    logger.warning(f"Story {i} is not a dict: {type(s)}")
                    continue

                stories.append(
                    UserStory(
                        id=f"US-{i:03d}",
                        persona=s.get("persona", "User"),
                        want=s.get("want", ""),
                        so_that=s.get("so_that", ""),
                        acceptance_criteria=s.get("acceptance_criteria", []),
                        dependencies=s.get("dependencies", []),
                        risks=s.get("risks", []),
                    )
                )

            print(f"[Stage 2 - LLM] Successfully parsed {len(stories)} stories", flush=True)
            return stories

        except Exception as e:
            logger.error(f"LLM decomposition failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _rule_based_decompose(
        self, requirements: list[dict[str, Any]], brief: RequirementBrief
    ) -> list[UserStory]:
        """Fallback rule-based story decomposition."""
        stories = []
        story_counter = 1

        for req in requirements:
            persona = req.get("as_a", "User").strip()
            want = req.get("i_want", "").strip()
            so_that = req.get("so_that", "").strip()
            acceptance_criteria = req.get("acceptance_criteria", [])

            story_id = f"US-{story_counter:03d}"
            story_counter += 1

            stories.append(
                UserStory(
                    id=story_id,
                    persona=persona,
                    want=want,
                    so_that=so_that,
                    acceptance_criteria=acceptance_criteria,
                )
            )

        if not stories:
            stories = self._generate_from_brief(brief)

        return stories

    def _generate_from_brief(self, brief: RequirementBrief) -> list[UserStory]:
        """Generate stories from brief if state is empty."""
        stories = []

        for i, need in enumerate(brief.functional_needs, 1):
            persona = brief.personas[0].name if brief.personas else "User"

            stories.append(
                UserStory(
                    id=f"US-{i:03d}",
                    persona=persona,
                    want=need,
                    so_that=brief.business_goal,
                    acceptance_criteria=[f"System should {need}"],
                )
            )

        # Last-resort fallback: if brief has no functional needs either,
        # create a single placeholder story so downstream stages don't crash.
        if not stories:
            persona = brief.personas[0].name if brief.personas else "User"
            stories.append(
                UserStory(
                    id="US-001",
                    persona=persona,
                    want=f"interact with {brief.title or 'the system'}",
                    so_that=brief.business_goal or "achieve business objectives",
                    acceptance_criteria=[
                        "Placeholder AC - requirements need clarification",
                        "Review Stage 1 open questions before proceeding",
                    ],
                )
            )
            logger.warning(
                "No stories or functional needs found. Generated placeholder story. "
                "Review the source document for clearer requirements."
            )

        return stories

    def _create_jira_cards(
        self, stories: list[UserStory], project_key: str
    ) -> dict[str, str]:
        """
        Create comprehensive Jira issues for each user story with all details.

        Creates cards with:
        - Comprehensive description (User Story, AC, DoD, Scope, Risks)
        - Story points estimation
        - Labels and components
        - Priority based on context
        - Epic linkage (if applicable)

        Returns mapping: { internal_story_id -> jira_issue_key }
        e.g. { "US-001" -> "KAN-123" }
        """
        jira_links: dict[str, str] = {}
        is_real = type(self.jira).__name__ == "JiraClient"
        mode = "REAL Jira" if is_real else "Mock Jira"

        logger.info(f"[{mode}] Creating {len(stories)} comprehensive Jira issues in project {project_key}")
        print(f"[Stage 2 - Jira] {mode}: Creating {len(stories)} comprehensive cards...", flush=True)

        # Optional: Create epic first if multiple related stories
        epic_key = None
        if len(stories) > 3:
            epic_key = self._create_epic_if_needed(stories, project_key)
            if epic_key:
                print(f"[Stage 2 - Jira] Created epic: {epic_key}", flush=True)

        for idx, story in enumerate(stories, 1):
            try:
                # Estimate story points based on complexity
                story_points = self._estimate_story_points(story)

                # Create comprehensive Jira card
                if is_real:
                    issue_key = self.jira.create_story(
                        story=story,
                        epic_key=epic_key,
                        story_points=story_points
                    )
                else:
                    issue_key = self.jira.create_story(story)

                jira_links[story.id] = issue_key

                logger.info(
                    f"Created {issue_key} for {story.id} "
                    f"(points: {story_points}, epic: {epic_key or 'none'})"
                )
                print(
                    f"[Stage 2 - Jira] [{idx}/{len(stories)}] ✓ {story.id} -> {issue_key} "
                    f"({story_points} pts): {story.want[:50]}",
                    flush=True
                )

            except Exception as e:
                logger.error(f"Failed to create Jira issue for {story.id}: {e}")
                print(f"[Stage 2 - Jira] [FAIL] {story.id} failed: {e}", flush=True)
                # Don't break the pipeline if a single issue fails

        print(f"\n[Stage 2 - Jira] Summary:", flush=True)
        print(f"  ✓ Created: {len(jira_links)}/{len(stories)} cards", flush=True)
        if epic_key:
            print(f"  ✓ Epic: {epic_key}", flush=True)
        print(flush=True)

        return jira_links

    def _create_backlog(
        self,
        brief: RequirementBrief,
        stories: list[UserStory],
        jira_links: dict[str, str],
    ) -> StoryBacklog:
        """Create StoryBacklog model."""
        backlog = StoryBacklog(
            brief_title=brief.title,
            stories=stories,
            approved=False,  # Needs PO approval
        )

        # Add metadata for tracking
        # Set generation source based on actual path taken:
        # "llm" if Claude was used, "rules" if fell back to rule-based
        generation_path = getattr(self, "_generation_path", "rules")
        backlog.__dict__["_generation_source"] = generation_path  # "llm" or "rules"
        backlog.__dict__["_generation_backend"] = self.llm.backend
        backlog.__dict__["_generation_detail"] = getattr(self, "_generation_detail", "")
        backlog.__dict__["_jira_links"] = jira_links
        backlog.__dict__["_source"] = brief.source

        return backlog

    def _update_state(self, backlog: StoryBacklog):
        """Update state file with backlog info."""
        if not self.state_file.exists():
            return

        with open(self.state_file, "r", encoding="utf-8") as f:
            state = json.load(f)

        # Update stage
        state["stage"] = "plan"
        state["backlog_created_at"] = datetime.now(timezone.utc).isoformat()
        state["total_stories"] = len(backlog.stories)

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        logger.info(f"Updated state file: {self.state_file}")


    def _estimate_story_points(self, story: UserStory) -> int:
        """
        Estimate story points using Fibonacci scale (1, 2, 3, 5, 8, 13).

        Factors:
        - Complexity: Number of acceptance criteria
        - Dependencies: External service integrations
        - Risk: Unknown/uncertain factors
        - Scope: Amount of work

        Returns:
            Story points (1-13)
        """
        points = 0

        # Base complexity from acceptance criteria
        ac_count = len(story.acceptance_criteria)
        if ac_count <= 2:
            points += 1
        elif ac_count <= 4:
            points += 3
        else:
            points += 5

        # Add points for dependencies
        dep_count = len(story.dependencies) if story.dependencies else 0
        if dep_count > 0:
            points += 2

        # Add points for risks/unknowns
        risk_count = len(story.risks) if story.risks else 0
        if risk_count > 0:
            points += 1

        # Add points for complex operations (keywords)
        want_lower = story.want.lower()
        complex_keywords = [
            "integrate", "migration", "security", "authentication",
            "encryption", "audit", "compliance", "workflow"
        ]
        if any(k in want_lower for k in complex_keywords):
            points += 2

        # Map to Fibonacci scale
        fibonacci = [1, 2, 3, 5, 8, 13]
        for fib in fibonacci:
            if points <= fib:
                return fib

        return 13  # Max points for very complex stories

    def _create_epic_if_needed(self, stories: list[UserStory], project_key: str) -> str | None:
        """
        Create an epic to group related stories (if applicable).

        Creates epic only if:
        - More than 3 stories
        - Real Jira client (not mock)

        Returns:
            Epic key (e.g., "KAN-100") or None
        """
        is_real = type(self.jira).__name__ == "JiraClient"

        if not is_real or len(stories) < 3:
            return None

        try:
            # Extract common theme from stories
            epic_name = self._extract_epic_name(stories)

            # Create epic
            epic_dict = {
                'project': {'key': project_key},
                'summary': epic_name,
                'description': self._build_epic_description(stories),
                'issuetype': {'name': 'Epic'},
            }

            # Try to set epic name (custom field)
            try:
                epic_dict['customfield_10011'] = epic_name  # Common Epic Name field
            except Exception:
                pass

            epic = self.jira.jira.create_issue(fields=epic_dict)
            logger.info(f"Created epic {epic.key}: {epic_name}")
            return epic.key

        except Exception as e:
            logger.warning(f"Failed to create epic: {e}")
            return None

    def _extract_epic_name(self, stories: list[UserStory]) -> str:
        """Extract a meaningful epic name from stories."""
        # Use the brief title or extract common theme
        state = self.load_state(self.root_dir)
        if state and state.get("epic"):
            return state["epic"]

        # Fallback: extract from story wants
        wants = [s.want for s in stories]
        common_words = set(wants[0].lower().split())

        for want in wants[1:]:
            common_words &= set(want.lower().split())

        if common_words:
            return " ".join(sorted(common_words)[:3]).title()

        return "Feature Development"

    def _build_epic_description(self, stories: list[UserStory]) -> str:
        """Build epic description summarizing all stories."""
        lines = [
            "h2. Epic Overview",
            "",
            f"This epic groups {len(stories)} related user stories.",
            "",
            "h2. Stories Included",
            ""
        ]

        for story in stories:
            lines.append(f"* {story.id}: {story.persona} - {story.want}")

        lines.append("")
        lines.append("h2. Business Value")
        if stories:
            lines.append(f"* {stories[0].so_that}")

        return "".join(lines)
