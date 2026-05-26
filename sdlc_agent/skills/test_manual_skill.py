"""
Automated implementation of /sdlc-test-manual skill for UI integration.

This module implements the logic from .claude/skills/sdlc-test-manual/SKILL.md
for generating detailed manual test cases using Anthropic API.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..integrations.anthropic_client import MockClaudeClient
from ..models import UserStory

logger = logging.getLogger(__name__)


class TestManualSkillAutomation:
    """Automates the /sdlc-test-manual skill logic."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.state_file = root_dir / ".claude" / "sdlc-state.json"
        self.llm = MockClaudeClient()

    def run(self, run_id: str) -> dict[str, Any]:
        """
        Execute the /sdlc-test-manual skill logic.

        Args:
            run_id: The run ID for organizing outputs

        Returns:
            dict with generated manual test cases
        """
        # Step 1: Load approved stories
        stories = self._load_approved_stories()
        if not stories:
            raise ValueError("No approved stories found in sdlc-state.json")

        # Step 2: Generate test cases for each story
        all_test_cases = []
        tc_counter = 1

        for story in stories:
            test_cases = self._generate_test_cases_for_story(story, tc_counter)
            all_test_cases.extend(test_cases)
            tc_counter += len(test_cases)

        # Step 3: Save test cases
        result = self._save_test_cases(run_id, all_test_cases)

        logger.info(
            f"Generated {len(all_test_cases)} manual test cases "
            f"across {len(stories)} stories"
        )

        return result

    def _load_approved_stories(self) -> list[UserStory]:
        """Load approved user stories from state file."""
        if not self.state_file.exists():
            return []

        with open(self.state_file, "r", encoding="utf-8") as f:
            state = json.load(f)

        # Convert state stories to UserStory objects
        stories = []
        for s in state.get("stories", []):
            stories.append(
                UserStory(
                    id=s.get("id", ""),
                    persona=s.get("as_a", ""),
                    want=s.get("i_want", ""),
                    so_that=s.get("so_that", ""),
                    acceptance_criteria=s.get("acceptance_criteria", []),
                )
            )

        return stories

    def _generate_test_cases_for_story(
        self, story: UserStory, start_id: int
    ) -> list[dict[str, Any]]:
        """Use LLM to generate detailed test cases for a story."""
        system_prompt = """You are a QA engineer creating detailed manual test cases.
For each acceptance criterion, generate a comprehensive test case with:
- Test steps (numbered, clear actions)
- Test data (specific inputs to use)
- Expected results (what should happen)
- Priority (High/Medium/Low)
- Type (Functional/UI/API/Performance/Security)

Return JSON array with this structure:
[
  {
    "title": "Test case title",
    "steps": ["1. Action", "2. Action", "3. Action"],
    "test_data": "Specific data to use",
    "expected_result": "What should happen",
    "priority": "High",
    "type": "Functional"
  }
]

Generate 1-3 test cases per acceptance criterion covering positive, negative, and edge cases."""

        user_prompt = f"""Story: {story.id}
As a: {story.persona}
I want: {story.want}
So that: {story.so_that}

Acceptance Criteria:
{chr(10).join(f"- {ac}" for ac in story.acceptance_criteria)}

Generate detailed test cases for each acceptance criterion."""

        result = self.llm.complete_json(
            system=system_prompt, user=user_prompt, max_tokens=4096, temperature=0.3
        )

        # Process LLM result
        test_cases = []
        if result and isinstance(result, list):
            for i, tc in enumerate(result):
                test_cases.append(
                    {
                        "tc_id": f"TC-{start_id + i:03d}",
                        "story_id": story.id,
                        "title": tc.get("title", "Untitled test case"),
                        "steps": tc.get("steps", []),
                        "test_data": tc.get("test_data", ""),
                        "expected_result": tc.get("expected_result", ""),
                        "priority": tc.get("priority", "Medium"),
                        "type": tc.get("type", "Functional"),
                    }
                )

        # Fallback if LLM doesn't return proper format
        if not test_cases:
            for i, ac in enumerate(story.acceptance_criteria):
                test_cases.append(
                    {
                        "tc_id": f"TC-{start_id + i:03d}",
                        "story_id": story.id,
                        "title": f"Verify {ac[:50]}",
                        "steps": [
                            "1. Set up test environment",
                            f"2. Perform action to test: {ac}",
                            "3. Verify expected result",
                        ],
                        "test_data": "TBD",
                        "expected_result": ac,
                        "priority": "High",
                        "type": "Functional",
                    }
                )

        return test_cases

    def _save_test_cases(self, run_id: str, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
        """Save test cases to JSON file."""
        runs_dir = self.root_dir / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)

        output_file = runs_dir / "manual_test_cases.json"
        result = {
            "run_id": run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_test_cases": len(test_cases),
            "test_cases": test_cases,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved manual test cases to {output_file}")

        # Also generate Excel file (optional)
        try:
            self._generate_excel(runs_dir / "manual_test_cases.xlsx", test_cases)
        except Exception as e:
            logger.warning(f"Failed to generate Excel file: {e}")

        return result

    def _generate_excel(self, output_path: Path, test_cases: list[dict[str, Any]]):
        """Generate Excel file for QA team (optional, requires openpyxl)."""
        try:
            from openpyxl import Workbook
        except ImportError:
            logger.info("openpyxl not installed, skipping Excel generation")
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Manual Test Cases"

        # Headers
        headers = ["TC ID", "Story ID", "Title", "Steps", "Test Data", "Expected Result", "Priority", "Type"]
        ws.append(headers)

        # Data rows
        for tc in test_cases:
            ws.append([
                tc["tc_id"],
                tc["story_id"],
                tc["title"],
                "\n".join(tc["steps"]),
                tc["test_data"],
                tc["expected_result"],
                tc["priority"],
                tc["type"],
            ])

        wb.save(output_path)
        logger.info(f"Generated Excel file at {output_path}")
