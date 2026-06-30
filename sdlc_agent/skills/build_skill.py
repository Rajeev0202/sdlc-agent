"""
Automated implementation of /sdlc-build skill for UI integration.

This module implements the logic from .claude/skills/sdlc-build/SKILL.md
for TDD-based code implementation with LLM intelligence.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..integrations.anthropic_client import ClaudeClient
from ..integrations import GitOperations, GitHubRestClient
from ..core.models import StoryBacklog, PullRequest, CodeFile
from ..guardrails import CodeQualityGuardrails, format_guardrail_report
from ..core.github_config import should_use_real_github
from ..core.code_layout import (
    get_implementation_path,
    get_test_path,
    get_controller_path,
    get_service_path,
    create_directories_for_story,
    get_layout_config,
    LayoutStyle,
)

logger = logging.getLogger(__name__)


class BuildSkillAutomation:
    """Automates the /sdlc-build skill logic with LLM-powered code generation."""

    def __init__(self, root_dir: Path, enable_guardrails: bool = True):
        self.root_dir = root_dir
        self.state_file = root_dir / ".claude" / "sdlc-state.json"
        self.llm = ClaudeClient()
        # Track LLM usage so we can fast-fail to templates if calls keep failing
        self._llm_failures = 0
        self._llm_max_failures = 2  # After 2 fails, stop trying LLM
        self._llm_successes = 0
        # Initialize guardrails for code quality validation
        self.guardrails = CodeQualityGuardrails(strict_mode=True) if enable_guardrails else None
        self._guardrail_rejections = 0  # Track how many times guardrails reject code
        # Initialize git operations for committing code
        self.git_ops = GitOperations()
        # Initialize GitHub client if token is available
        self.use_real_github = should_use_real_github()
        self.github = GitHubRestClient() if self.use_real_github else None
        logger.info(f"BuildSkillAutomation initialized with backend: {self.llm.backend}, "
                   f"guardrails: {'enabled' if enable_guardrails else 'disabled'}, "
                   f"github: {'real' if self.use_real_github else 'mock'}")

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

        # Step 2: Commit files to git (ALWAYS, even without GitHub token)
        branch_name = f"feature/{backlog.brief_title.lower().replace(' ', '-')}"
        self._commit_files_to_git(code_files, backlog, branch_name)

        # Step 3: Create pull request model
        pr = self._create_pull_request(backlog, code_files, branch_name)

        # Step 4: Create real GitHub PR if token is available
        if self.github:
            pr = self._create_github_pr(pr)

        # Step 5: Update state
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

        # OPTIMIZATION: Try batch generation first (1 LLM call for all stories)
        # Falls back to per-story generation if batch fails
        batch_enabled = os.environ.get("STAGE3_BATCH_MODE", "1") == "1"
        if batch_enabled and self.llm.is_live and total > 1:
            print(f"[Stage 3] 💰 Attempting BATCH generation (1 LLM call for {total} stories)...", flush=True)
            batch_files = self._llm_generate_batch(backlog.stories)
            if batch_files:
                self._llm_successes += len(batch_files)
                files.extend(batch_files)
                print(f"[Stage 3] 💰 Batch SUCCESS: saved ~{total * 2 - 1} LLM calls!", flush=True)

                if inject_defect and files:
                    files[0] = self._inject_defect(files[0])
                    logger.info(f"Injected defect in {files[0].path} for demo purposes")

                return files
            else:
                print(f"[Stage 3] Batch failed, falling back to per-story generation", flush=True)

        # Check if we're using Controller-Service architecture
        layout_config = get_layout_config()
        is_controller_service = (
            layout_config.style == LayoutStyle.CONTROLLER_SERVICE
            and layout_config.default_layer == "both"
        )

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

            if is_controller_service:
                # Generate both controller and service
                controller_file = self._generate_controller(story)
                service_file = self._generate_service(story)
                files.append(controller_file)
                files.append(service_file)

                # Generate tests for both
                controller_test = self._generate_controller_test(story)
                service_test = self._generate_service_test(story)
                files.append(controller_test)
                files.append(service_test)
            else:
                # Standard single-file generation
                impl_file = self._generate_implementation(story)
                files.append(impl_file)

                # Generate test file (TDD approach)
                test_file = self._generate_test_file(story)
                files.append(test_file)

        print(f"\n[Stage 3] Generation Complete:")
        print(f"  ✓ LLM successes: {self._llm_successes}")
        print(f"  ✗ LLM failures: {self._llm_failures}")
        print(f"  📋 Fallback templates used: {total - self._llm_successes}")
        if self.guardrails:
            print(f"  🛡️  Guardrail rejections: {self._guardrail_rejections}")
        print(flush=True)

        # Optionally inject a defect for demo
        if inject_defect and files:
            files[0] = self._inject_defect(files[0])
            logger.info(f"Injected defect in {files[0].path} for demo purposes")

        return files

    def _generate_implementation(self, story) -> CodeFile:
        """Generate implementation code for a story using LLM (with fast-fail)."""
        # Use the configurable layout system for file paths
        file_path = get_implementation_path(story)

        # Create necessary directories
        create_directories_for_story(story)

        # Skip LLM if we've already hit too many failures
        if self.llm.is_live and self._llm_failures < self._llm_max_failures:
            llm_code = self._llm_generate_implementation(story)
            if llm_code:
                # Validate with guardrails before accepting
                code_file = CodeFile(
                    path=file_path,
                    contents=llm_code,
                    language="python",
                )

                if self._validate_with_guardrails(code_file, story):
                    self._llm_successes += 1
                    return code_file
                else:
                    # Guardrails rejected - treat as LLM failure
                    logger.warning(f"Guardrails rejected LLM code for {story.id}, falling back to template")
                    self._guardrail_rejections += 1

            self._llm_failures += 1
            logger.warning(
                f"LLM code generation failed for {story.id} "
                f"({self._llm_failures}/{self._llm_max_failures}), using template"
            )

        # Fallback: template-based generation
        template_code = self._template_implementation(story)

        # Validate template code with guardrails too
        if not self._validate_with_guardrails(template_code, story):
            logger.error(f"Even template code failed guardrails for {story.id} - this shouldn't happen!")

        return template_code

    def _llm_generate_batch(self, stories: list) -> list[CodeFile]:
        """Generate implementation + test code for ALL stories in ONE LLM call.

        Returns list of CodeFile objects (impl + test for each story) or empty list on failure.
        This saves significant cost — 2N calls becomes 1 call.
        """
        if not stories:
            return []

        system_prompt = """You are a senior Python engineer at NatWest writing production code for MULTIPLE user stories.

CODING STANDARDS (MANDATORY):
- Use logging.getLogger(__name__) NEVER print()
- TLS verification enabled (verify=True)
- NO hardcoded credentials, tokens, or PII
- NO eval, exec, or subprocess(shell=True)
- Every public function/class must have a docstring
- Type hints on all function signatures

SECURITY REQUIREMENTS:
- Authentication: Accept user_id parameter and validate it
- Authorization: Add ownership/permission checks
- Audit logging: Log all sensitive operations
- Input validation: Validate all inputs
- Error handling: Wrap operations in try-except

OUTPUT FORMAT — Return a single JSON object with this exact structure:
{
  "files": [
    {"story_id": "US-001", "type": "impl", "code": "...python code..."},
    {"story_id": "US-001", "type": "test", "code": "...pytest code..."},
    {"story_id": "US-002", "type": "impl", "code": "..."},
    {"story_id": "US-002", "type": "test", "code": "..."}
  ]
}

For each story, generate:
1. An implementation class named <UpperCamelCase(id)>Feature with execute() method
2. A pytest test file importing from src/<lowercase_id>.py

Return ONLY the JSON, no markdown."""

        # Build user prompt with ALL stories
        stories_brief = []
        for s in stories:
            ac_text = "\n  ".join(s.acceptance_criteria) if s.acceptance_criteria else "N/A"
            stories_brief.append(
                f"- {s.id}: As {s.persona}, I want {s.want}, so that {s.so_that}.\n"
                f"  Acceptance criteria:\n  {ac_text}"
            )
        user_prompt = (
            f"Generate code for these {len(stories)} user stories:\n\n"
            + "\n\n".join(stories_brief)
        )

        try:
            # Allow large output for many stories
            result = self.llm.complete_json(
                system=system_prompt,
                user=user_prompt,
                max_tokens=8192,
                temperature=0.2,
            )
        except Exception as exc:
            logger.warning(f"Batch generation crashed: {exc}")
            return []

        if not result or not isinstance(result, dict) or "files" not in result:
            logger.warning("Batch LLM did not return expected JSON structure")
            return []

        # Convert response to CodeFile objects
        code_files: list[CodeFile] = []
        files_data = result.get("files", [])
        for entry in files_data:
            if not isinstance(entry, dict):
                continue
            story_id = entry.get("story_id", "")
            file_type = entry.get("type", "")
            code = entry.get("code", "")
            if not story_id or not code:
                continue

            # Find the story object to get proper paths
            story = next((s for s in stories if s.id == story_id), None)
            if not story:
                logger.warning(f"Batch generation returned {story_id} but no matching story found")
                continue

            if file_type == "test":
                path = get_test_path(story)
            else:
                path = get_implementation_path(story)
                # Create directories for this story
                create_directories_for_story(story)

            cf = CodeFile(path=path, contents=code, language="python")

            # Run guardrails on each generated file
            story = next((s for s in stories if s.id == story_id), None)
            if story and not self._validate_with_guardrails(cf, story):
                logger.warning(f"Batch file {path} rejected by guardrails")
                self._guardrail_rejections += 1
                continue

            code_files.append(cf)

        # Verify we got both impl + test for each story
        expected = len(stories) * 2
        if len(code_files) < expected * 0.7:  # Allow some guardrail rejections
            logger.warning(
                f"Batch returned only {len(code_files)}/{expected} files; will retry per-story"
            )
            return []

        return code_files

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
- Include proper error handling with try-except blocks
- Add comprehensive input validation (check types, required fields, bounds)
- Use meaningful variable names
- Keep functions under 50 lines
- Use dependency injection where appropriate

SECURITY REQUIREMENTS (CRITICAL - ALL must be present):
- Authentication: Accept user_id parameter and validate it's not None/empty
- Authorization: Add ownership/permission checks (e.g., verify user owns the resource)
- Audit logging: Log all sensitive operations (user_id, action, timestamp, result)
- Input validation: Validate all inputs (type checking, required fields, sanitization)
- Error handling: Wrap operations in try-except, don't expose internal errors

IMPLEMENTATION PATTERN:
1. Validate inputs (raise ValueError if invalid)
2. Check authorization (raise PermissionError if unauthorized)
3. Perform operation with try-except
4. Log audit trail
5. Return structured response

Return ONLY Python code, no markdown formatting, no explanations."""

        user_prompt = f"""Story: {story.id}
As a: {story.persona}
I want: {story.want}
So that: {story.so_that}

Acceptance Criteria:
{chr(10).join(f"- {ac}" for ac in story.acceptance_criteria)}

Generate complete Python implementation that:
1. Implements all acceptance criteria with REAL business logic (not stubs)
2. Follows ALL NatWest coding standards (logging, no print(), TLS enabled)
3. MUST include security controls:
   - Accept user_id parameter for authentication
   - Add authorization checks (verify user owns/can access the resource)
   - Log all operations with audit trail (user_id, action, timestamp, result)
   - Validate ALL inputs (type checking, required fields, bounds)
   - Wrap operations in try-except with proper error handling
4. Is production-ready and testable (uses dependency injection)
5. Returns structured responses {{"success": bool, "message": str, "result": dict}}

CRITICAL: Include all 5 security controls above or the code will be rejected.

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

    def __init__(self, audit_service=None, auth_service=None):
        """
        Initialize {class_name}.

        Args:
            audit_service: Service for audit logging (injected dependency)
            auth_service: Service for authorization checks (injected dependency)
        """
        self.audit_service = audit_service
        self.auth_service = auth_service
        self.initialized = True
        logger.info("%s initialized", self.__class__.__name__)

    def execute(self, user_id: str = None, **kwargs):
        """
        Execute the main functionality.

        Acceptance Criteria:
{chr(10).join(f"        - {ac}" for ac in story.acceptance_criteria)}

        Args:
            user_id: Authenticated user ID (required for security)
            **kwargs: Additional parameters as needed

        Returns:
            dict: Result with success status and message

        Raises:
            ValueError: If inputs are invalid
            PermissionError: If user is not authorized
        """
        # 1. Input validation
        if not user_id:
            logger.error("Missing required parameter: user_id")
            raise ValueError("user_id is required for authentication")

        # Validate other required parameters based on acceptance criteria
        required_fields = []  # TODO: Extract from acceptance criteria
        for field in required_fields:
            if field not in kwargs or not kwargs[field]:
                raise ValueError(f"Missing required parameter: {{field}}")

        try:
            # 2. Authorization check
            if self.auth_service and not self.auth_service.is_authorized(user_id, kwargs):
                logger.warning("Authorization failed for user %s", user_id)
                raise PermissionError(f"User {{user_id}} is not authorized for this operation")

            # 3. Business logic implementation
            logger.info("Executing %s for user %s", self.__class__.__name__, user_id)

            # TODO: Implement actual business logic based on acceptance criteria
            # This is a template - replace with real implementation
            result = self._perform_operation(user_id, **kwargs)

            # 4. Audit logging
            if self.audit_service:
                self.audit_service.log_action(
                    user_id=user_id,
                    action=self.__class__.__name__,
                    result="success",
                    details=kwargs
                )

            return {{"success": True, "message": "Operation completed successfully", "result": result}}

        except Exception as e:
            # 5. Error handling and audit logging
            logger.error("Operation failed for user %s: %s", user_id, str(e), exc_info=True)

            if self.audit_service:
                self.audit_service.log_action(
                    user_id=user_id,
                    action=self.__class__.__name__,
                    result="failure",
                    error=str(e)
                )

            # Don't expose internal errors to caller
            raise RuntimeError("Operation failed. Please try again or contact support.")

    def _perform_operation(self, user_id: str, **kwargs):
        """
        Perform the actual business operation.

        Override this method with specific business logic based on acceptance criteria.
        """
        # Template implementation - replace with actual business logic
        return {{"status": "completed"}}

    def validate(self):
        """Validate the implementation meets acceptance criteria."""
        return self.initialized
'''

        return CodeFile(
            path=get_implementation_path(story),
            contents=code,
            language="python",
        )

    def _generate_test_file(self, story) -> CodeFile:
        """Generate test file for a story (TDD approach) using LLM (with fast-fail)."""
        # Use the configurable layout system for file paths
        file_path = get_test_path(story)

        # Skip LLM if we've already hit too many failures
        if self.llm.is_live and self._llm_failures < self._llm_max_failures:
            llm_tests = self._llm_generate_tests(story)
            if llm_tests:
                self._llm_successes += 1
                return CodeFile(
                    path=file_path,
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
            path=get_test_path(story),
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

    def _validate_with_guardrails(self, code_file: CodeFile, story) -> bool:
        """
        Validate generated code with quality guardrails.

        Args:
            code_file: The code file to validate
            story: The story context for validation

        Returns:
            True if code passes guardrails, False otherwise
        """
        if not self.guardrails:
            # Guardrails disabled - accept all code
            return True

        # Prepare context for guardrails
        context = {
            "story_id": story.id,
            "persona": story.persona,
            "want": story.want,
        }

        print(f"\n🛡️  Running guardrails on {code_file.path}...")

        # Run guardrail validation
        result = self.guardrails.validate(code_file.contents, context)

        # Print detailed report
        report = format_guardrail_report(result)
        print(report)

        if not result.passed:
            print(f"❌ Code REJECTED by guardrails (score: {result.score:.1f}/100)")
            logger.warning(
                f"Guardrails rejected {code_file.path}: {len(result.blocking_violations())} blocking violations"
            )
        else:
            print(f"✅ Code ACCEPTED by guardrails (score: {result.score:.1f}/100)")
            logger.info(f"Guardrails passed for {code_file.path} (score: {result.score:.1f})")

        return result.passed

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

    def _commit_files_to_git(
        self, files: list[CodeFile], backlog: StoryBacklog, branch_name: str
    ) -> None:
        """Commit generated files to git."""
        print(f"\n[Stage 3] 📝 Committing files to git...", flush=True)

        try:
            # Create branch
            self.git_ops.create_branch(branch_name)
            logger.info(f"Created branch: {branch_name}")
            print(f"[Stage 3] ✅ Created branch: {branch_name}", flush=True)
        except Exception as exc:
            logger.warning(f"Could not create branch (may already exist): {exc}")
            print(f"[Stage 3] ⚠️  Using existing branch or current location", flush=True)

        # Write files to disk
        written_paths = self.git_ops.write_files(files)
        logger.info(f"Wrote {len(written_paths)} files to disk")
        print(f"[Stage 3] ✅ Wrote {len(written_paths)} files to disk", flush=True)

        # Stage files
        self.git_ops.stage_files(written_paths)
        logger.info(f"Staged {len(written_paths)} files")

        # Check if there are actually changes to commit
        if not self.git_ops.has_uncommitted_changes():
            print(f"[Stage 3] ℹ️  No changes to commit (files may be identical)", flush=True)
            return

        # Commit changes
        commit_message = f"feat: {backlog.brief_title}"
        try:
            commit_sha = self.git_ops.commit_changes(commit_message, backlog)
            logger.info(f"Committed changes: {commit_sha[:8]}")
            print(f"[Stage 3] ✅ Committed: {commit_sha[:8]}", flush=True)
        except Exception as exc:
            logger.error(f"Failed to commit changes: {exc}")
            print(f"[Stage 3] ❌ Failed to commit: {exc}", flush=True)
            raise

        # Push to remote (only if using real GitHub)
        if self.github:
            try:
                self.git_ops.push_branch(branch_name)
                logger.info(f"Pushed branch {branch_name} to remote")
                print(f"[Stage 3] ✅ Pushed branch to GitHub", flush=True)
            except Exception as exc:
                logger.warning(f"Failed to push branch: {exc}")
                print(f"[Stage 3] ⚠️  Failed to push (branch may already exist on remote)", flush=True)
        else:
            print(f"[Stage 3] ℹ️  Branch not pushed (GITHUB_TOKEN not set)", flush=True)

    def _create_pull_request(
        self, backlog: StoryBacklog, files: list[CodeFile], branch_name: str
    ) -> PullRequest:
        """Create pull request model."""
        # Generate PR number
        pr_number = self._get_next_pr_number()

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

    def _create_github_pr(self, pr: PullRequest) -> PullRequest:
        """Create actual GitHub PR if token is available."""
        if not self.github:
            return pr

        print(f"\n[Stage 3] 🚀 Creating GitHub PR...", flush=True)
        try:
            github_pr = self.github.open_pull_request(
                branch=pr.branch,
                title=pr.title,
                body=pr.body,
                files=pr.files,
                story_ids=pr.story_ids,
            )
            print(f"[Stage 3] ✅ GitHub PR created: #{github_pr.number}", flush=True)
            logger.info(f"Created GitHub PR: #{github_pr.number}")
            return github_pr
        except Exception as exc:
            logger.error(f"Failed to create GitHub PR: {exc}")
            print(f"[Stage 3] ⚠️  Failed to create GitHub PR: {exc}", flush=True)
            # Return the local PR model
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


    # ============================================================================
    # Controller-Service Architecture Methods
    # ============================================================================

    def _generate_controller(self, story) -> CodeFile:
        """Generate controller file for Controller-Service architecture."""
        controller_path = get_controller_path(story)
        # Placeholder - will be implemented in next iteration
        return CodeFile(
            path=controller_path,
            contents='# Controller placeholder',
            language='python',
        )

    def _generate_service(self, story) -> CodeFile:
        """Generate service file for Controller-Service architecture."""
        service_path = get_service_path(story)
        # Placeholder - will be implemented in next iteration
        return CodeFile(
            path=service_path,
            contents='# Service placeholder',
            language='python',
        )

    def _generate_controller_test(self, story) -> CodeFile:
        """Generate test file for controller."""
        controller_path = get_controller_path(story)
        test_path = controller_path.replace('src/', 'tests/').replace('.py', '_test.py')
        return CodeFile(
            path=test_path,
            contents='# Controller test placeholder',
            language='python',
        )

    def _generate_service_test(self, story) -> CodeFile:
        """Generate test file for service."""
        service_path = get_service_path(story)
        test_path = service_path.replace('src/', 'tests/').replace('.py', '_test.py')
        return CodeFile(
            path=test_path,
            contents='# Service test placeholder',
            language='python',
        )
