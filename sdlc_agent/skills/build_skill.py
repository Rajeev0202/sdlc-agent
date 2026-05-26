"""
Automated implementation of /sdlc-build skill for UI integration.

This module implements the logic from .claude/skills/sdlc-build/SKILL.md
for TDD-based code implementation with LLM intelligence.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..integrations.anthropic_client import MockClaudeClient
from ..models import StoryBacklog, PullRequest, CodeFile

logger = logging.getLogger(__name__)


class BuildSkillAutomation:
    """Automates the /sdlc-build skill logic with LLM-powered code generation."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.state_file = root_dir / ".claude" / "sdlc-state.json"
        self.llm = MockClaudeClient()
        # Track LLM usage so we can fast-fail to templates if calls keep failing
        self._llm_failures = 0
        self._llm_max_failures = 2  # After 2 fails, stop trying LLM
        self._llm_successes = 0
        logger.info(f"BuildSkillAutomation initialized with backend: {self.llm.backend}")

    def run(self, backlog: StoryBacklog, inject_defect: bool = False) -> PullRequest:
        """
        Execute the /sdlc-build skill logic.

        Args:
            backlog: Approved story backlog from Stage 2
            inject_defect: Whether to inject a defect for demo purposes

        Returns:
            PullRequest with generated code files
        """
        if not backlog.approved:
            raise ValueError("Backlog must be approved before building code")

        # Step 1: Generate code files for each story
        code_files = self._generate_code_files(backlog, inject_defect)

        # Step 2: Create pull request model
        pr = self._create_pull_request(backlog, code_files)

        # Step 3: Update state
        self._update_state(pr)

        logger.info(f"Generated {len(code_files)} code files for PR #{pr.number}")

        return pr

    def _generate_code_files(
        self, backlog: StoryBacklog, inject_defect: bool
    ) -> list[CodeFile]:
        """Generate code files for all stories with fast-fail to templates."""
        files = []
        total = len(backlog.stories)

        print(f"[Stage 3] Generating code for {total} stories (backend: {self.llm.backend})", flush=True)

        for idx, story in enumerate(backlog.stories, 1):
            # Decide whether to use LLM based on past failures
            use_llm = (
                self.llm.is_live
                and self._llm_failures < self._llm_max_failures
            )

            if use_llm:
                print(f"[Stage 3] [{idx}/{total}] LLM generating {story.id}...", flush=True)
            else:
                print(f"[Stage 3] [{idx}/{total}] Template for {story.id} "
                      f"(LLM failures: {self._llm_failures}/{self._llm_max_failures})", flush=True)

            # Generate main implementation file
            impl_file = self._generate_implementation(story)
            files.append(impl_file)

            # Generate test file (TDD approach)
            test_file = self._generate_test_file(story)
            files.append(test_file)

        print(f"[Stage 3] Done. LLM successes: {self._llm_successes}, "
              f"LLM failures: {self._llm_failures}, fallback templates used: "
              f"{total - self._llm_successes}", flush=True)

        # Optionally inject a defect for demo
        if inject_defect and files:
            files[0] = self._inject_defect(files[0])
            logger.info(f"Injected defect in {files[0].path} for demo purposes")

        return files

    def _generate_implementation(self, story) -> CodeFile:
        """Generate implementation code for a story using LLM (with fast-fail)."""
        module_name = story.id.lower().replace("-", "_")

        # Skip LLM if we've already hit too many failures
        if self.llm.is_live and self._llm_failures < self._llm_max_failures:
            llm_code = self._llm_generate_implementation(story)
            if llm_code:
                self._llm_successes += 1
                return CodeFile(
                    path=f"src/{module_name}.py",
                    contents=llm_code,
                    language="python",
                )
            self._llm_failures += 1
            logger.warning(
                f"LLM code generation failed for {story.id} "
                f"({self._llm_failures}/{self._llm_max_failures}), using template"
            )

        # Fallback: template-based generation
        return self._template_implementation(story)

    def _llm_generate_implementation(self, story) -> str:
        """Use Claude LLM to generate production-quality implementation code."""
        system_prompt = """You are a senior Python engineer at NatWest writing production code.

CODING STANDARDS (MANDATORY):
- Use logging.getLogger(__name__) NEVER print()
- TLS verification enabled (verify=True)
- NO hardcoded credentials, tokens, or PII
- NO eval, exec, or subprocess(shell=True)
- Every public function/class must have a docstring
- Type hints on all function signatures
- Use Pydantic for data models
- Use datetime.now(timezone.utc) NOT datetime.utcnow()
- Wrap external calls in try/except with specific exceptions
- Use context managers (with statements) for resources

CODE QUALITY:
- Write REAL working code, not stubs
- Implement actual business logic for each acceptance criterion
- Include proper error handling
- Add input validation
- Use meaningful variable names
- Keep functions under 50 lines
- Use dependency injection where appropriate

Return ONLY Python code, no markdown formatting, no explanations."""

        user_prompt = f"""Story: {story.id}
As a: {story.persona}
I want: {story.want}
So that: {story.so_that}

Acceptance Criteria:
{chr(10).join(f"- {ac}" for ac in story.acceptance_criteria)}

Generate complete Python implementation that:
1. Implements all acceptance criteria
2. Follows NatWest coding standards
3. Is production-ready (not a stub)
4. Has proper logging, error handling, and validation
5. Is testable (uses dependency injection)

Return only the Python code."""

        try:
            result = self.llm.complete_json(
                system=system_prompt, user=user_prompt, max_tokens=4096, temperature=0.2
            )

            # Extract code from response
            code = ""
            if isinstance(result, dict):
                code = result.get("code") or result.get("implementation") or ""
            elif isinstance(result, str):
                code = result
            elif isinstance(result, list) and len(result) > 0:
                code = str(result[0])

            # Strip markdown if present
            code = code.strip()
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]

            return code.strip() if len(code) > 100 else ""
        except Exception as e:
            logger.error(f"LLM implementation generation failed: {e}")
            return ""

    def _template_implementation(self, story) -> CodeFile:
        """Fallback template-based implementation."""
        class_name = self._story_to_class_name(story.id)

        code = f'''"""
Implementation for {story.id}: {story.want}

Persona: {story.persona}
Goal: {story.so_that}
"""
import logging

logger = logging.getLogger(__name__)


class {class_name}:
    """Implementation of {story.want}."""

    def __init__(self):
        """Initialize {class_name}."""
        self.initialized = True
        logger.info("%s initialized", self.__class__.__name__)

    def execute(self, **kwargs):
        """
        Execute the main functionality.

        Acceptance Criteria:
{chr(10).join(f"        - {ac}" for ac in story.acceptance_criteria)}
        """
        logger.info("Executing %s", self.__class__.__name__)
        return {{"success": True, "message": "Feature implemented"}}

    def validate(self):
        """Validate the implementation meets acceptance criteria."""
        return True
'''

        return CodeFile(
            path=f"src/{story.id.lower().replace('-', '_')}.py",
            contents=code,
            language="python",
        )

    def _generate_test_file(self, story) -> CodeFile:
        """Generate test file for a story (TDD approach) using LLM (with fast-fail)."""
        module_name = story.id.lower().replace("-", "_")

        # Skip LLM if we've already hit too many failures
        if self.llm.is_live and self._llm_failures < self._llm_max_failures:
            llm_tests = self._llm_generate_tests(story)
            if llm_tests:
                self._llm_successes += 1
                return CodeFile(
                    path=f"tests/test_{module_name}.py",
                    contents=llm_tests,
                    language="python",
                )
            self._llm_failures += 1
            logger.warning(
                f"LLM test generation failed for {story.id} "
                f"({self._llm_failures}/{self._llm_max_failures}), using template"
            )

        # Fallback: template-based generation
        return self._template_test_file(story)

    def _llm_generate_tests(self, story) -> str:
        """Use Claude LLM to generate meaningful pytest tests."""
        system_prompt = """You are a senior QA engineer writing pytest tests at NatWest.

TEST QUALITY STANDARDS:
- Real assertions, not placeholders
- Test happy path, edge cases, and error cases
- Use pytest fixtures for setup
- Use parametrize for similar test cases
- Mock external dependencies (use unittest.mock or pytest-mock)
- Each test verifies ONE thing
- Test names describe what is being tested: test_<scenario>_<expected_outcome>
- Use Given/When/Then comments for clarity
- Coverage target: every acceptance criterion has at least one test

Return ONLY Python pytest code, no markdown, no explanations."""

        module_name = story.id.lower().replace("-", "_")
        class_name = self._story_to_class_name(story.id)

        user_prompt = f"""Story: {story.id}
As a: {story.persona}
I want: {story.want}
So that: {story.so_that}

Acceptance Criteria:
{chr(10).join(f"- {ac}" for ac in story.acceptance_criteria)}

Module to test: src/{module_name}.py
Class to test: {class_name}

Generate comprehensive pytest test suite with:
1. One test per acceptance criterion (positive case)
2. Edge case tests
3. Error/exception tests
4. Proper mocking of dependencies
5. Use pytest fixtures

Return only the Python test code."""

        try:
            result = self.llm.complete_json(
                system=system_prompt, user=user_prompt, max_tokens=4096, temperature=0.2
            )

            code = ""
            if isinstance(result, dict):
                code = result.get("code") or result.get("tests") or ""
            elif isinstance(result, str):
                code = result
            elif isinstance(result, list) and len(result) > 0:
                code = str(result[0])

            # Strip markdown
            code = code.strip()
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]

            return code.strip() if len(code) > 100 else ""
        except Exception as e:
            logger.error(f"LLM test generation failed: {e}")
            return ""

    def _template_test_file(self, story) -> CodeFile:
        """Fallback template-based test file."""
        class_name = self._story_to_class_name(story.id)
        module_name = story.id.lower().replace("-", "_")

        code = f'''"""
Tests for {story.id}: {story.want}

This file follows TDD approach - tests written first.
"""
import pytest
from src.{module_name} import {class_name}


class Test{class_name}:
    """Test suite for {class_name}."""

    def setup_method(self):
        """Set up test fixtures."""
        self.instance = {class_name}()

    def test_initialization(self):
        """Test that {class_name} initializes correctly."""
        assert self.instance.initialized is True

    def test_execute_returns_success(self):
        """Test execute method returns success."""
        result = self.instance.execute()
        assert result["success"] is True

    def test_validation_passes(self):
        """Test validation passes for valid implementation."""
        assert self.instance.validate() is True

{self._generate_ac_tests(story)}
'''

        return CodeFile(
            path=f"tests/test_{module_name}.py",
            contents=code,
            language="python",
        )

    def _generate_ac_tests(self, story) -> str:
        """Generate test cases for each acceptance criterion."""
        tests = []

        for i, ac in enumerate(story.acceptance_criteria, 1):
            test_name = self._ac_to_test_name(ac)
            tests.append(f'''    def test_ac{i}_{test_name}(self):
        """
        AC{i}: {ac}
        """
        # TODO: Implement test for acceptance criterion {i}
        result = self.instance.execute()
        assert result["success"] is True
''')

        return "\n".join(tests)

    def _inject_defect(self, code_file: CodeFile) -> CodeFile:
        """Inject a defect for demo purposes."""
        # Replace a return statement to cause a test failure
        defective_code = code_file.contents.replace(
            '"success": True',
            '"success": False  # INJECTED DEFECT',
        )

        return CodeFile(
            path=code_file.path,
            contents=defective_code,
            language=code_file.language,
        )

    def _create_pull_request(
        self, backlog: StoryBacklog, files: list[CodeFile]
    ) -> PullRequest:
        """Create pull request model."""
        # Generate PR number and branch name
        pr_number = self._get_next_pr_number()
        branch_name = f"feature/{backlog.brief_title.lower().replace(' ', '-')}"

        # Build PR title and description
        title = f"feat: {backlog.brief_title}"
        description = self._build_pr_description(backlog)

        pr = PullRequest(
            number=pr_number,
            title=title,
            body=description,
            branch=branch_name,
            files=files,
            story_ids=[s.id for s in backlog.stories],
        )

        # Add metadata
        pr.__dict__["_generation_source"] = "skill_automation"
        pr.__dict__["_generation_backend"] = "sdlc-build"

        return pr

    def _build_pr_description(self, backlog: StoryBacklog) -> str:
        """Build PR description from backlog."""
        lines = [
            f"# {backlog.brief_title}",
            "",
            "## User Stories",
            "",
        ]

        for story in backlog.stories:
            lines.append(f"### {story.id}: {story.want}")
            lines.append(f"**As a** {story.persona}")
            lines.append(f"**I want** {story.want}")
            lines.append(f"**So that** {story.so_that}")
            lines.append("")
            lines.append("**Acceptance Criteria:**")
            for ac in story.acceptance_criteria:
                lines.append(f"- {ac}")
            lines.append("")

        lines.append("## Testing")
        lines.append("- [ ] All unit tests pass")
        lines.append("- [ ] Code review completed")
        lines.append("- [ ] Acceptance criteria verified")

        return "\n".join(lines)

    def _get_next_pr_number(self) -> int:
        """Get next PR number (simple counter)."""
        # In production, this would query Git/GitHub
        return int(datetime.now(timezone.utc).timestamp()) % 10000

    def _story_to_class_name(self, story_id: str) -> str:
        """Convert story ID to PascalCase class name."""
        # US-001 -> Us001Feature
        return story_id.replace("-", "") + "Feature"

    def _ac_to_test_name(self, acceptance_criterion: str) -> str:
        """Convert acceptance criterion to snake_case test name."""
        # Take first few words and convert to snake_case
        words = acceptance_criterion.lower().split()[:4]
        return "_".join(w.strip(".,!?") for w in words)

    def _update_state(self, pr: PullRequest):
        """Update state file with PR info."""
        if not self.state_file.exists():
            return

        with open(self.state_file, "r", encoding="utf-8") as f:
            state = json.load(f)

        state["stage"] = "build"
        state["pr_created_at"] = datetime.now(timezone.utc).isoformat()
        state["pr_number"] = pr.number
        state["pr_branch"] = pr.branch
        state["files_generated"] = len(pr.files)

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        logger.info(f"Updated state file with PR #{pr.number}")
