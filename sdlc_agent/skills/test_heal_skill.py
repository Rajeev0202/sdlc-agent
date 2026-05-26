"""
Automated implementation of /sdlc-test-heal skill for UI integration.

This module implements the logic from .claude/skills/sdlc-test-heal/SKILL.md
for analyzing test failures and generating healing suggestions using Anthropic API.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..integrations.anthropic_client import MockClaudeClient

logger = logging.getLogger(__name__)


class TestHealSkillAutomation:
    """Automates the /sdlc-test-heal skill logic."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.llm = MockClaudeClient()

    def run(self, run_id: str) -> dict[str, Any]:
        """
        Execute the /sdlc-test-heal skill logic.

        Args:
            run_id: The run ID for organizing outputs

        Returns:
            dict with healing suggestions for failed tests
        """
        # Step 1: Load test execution results
        execution_results = self._load_execution_results(run_id)
        if not execution_results:
            raise ValueError(
                f"No test execution results found for run {run_id}. "
                "Run /sdlc-test-execute first."
            )

        # Step 2: Filter failed tests
        failed_tests = [
            r for r in execution_results.get("results", [])
            if r["status"] == "failed"
        ]

        if not failed_tests:
            logger.info("No failed tests to heal")
            return {
                "run_id": run_id,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "failures_analyzed": 0,
                "auto_fixable": 0,
                "manual_review_needed": 0,
                "healing_suggestions": [],
            }

        # Step 3: Analyze each failure and generate healing suggestions
        healing_suggestions = []
        for failed_test in failed_tests:
            suggestion = self._analyze_failure(run_id, failed_test)
            healing_suggestions.append(suggestion)

        # Step 4: Save healing report
        result = self._save_healing_report(run_id, healing_suggestions)

        logger.info(
            f"Analyzed {len(failed_tests)} failures, "
            f"{result['auto_fixable']} auto-fixable"
        )

        return result

    def _load_execution_results(self, run_id: str) -> dict[str, Any]:
        """Load test execution results from JSON file."""
        results_file = self.root_dir / "runs" / run_id / "test_execution.json"
        if not results_file.exists():
            return {}

        with open(results_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _analyze_failure(self, run_id: str, failed_test: dict[str, Any]) -> dict[str, Any]:
        """Use LLM to analyze test failure and suggest fixes."""
        # Load the test script
        test_id = failed_test["test_id"]
        script_file = self._find_test_script(run_id, test_id)
        script_code = ""

        if script_file and script_file.exists():
            with open(script_file, "r", encoding="utf-8") as f:
                script_code = f.read()

        # Categorize failure
        error_msg = failed_test.get("error", "")
        category = self._categorize_failure(error_msg)

        # Generate healing suggestion using LLM
        system_prompt = """You are a QA debugging expert analyzing test failures.
For the given test failure, provide:
1. Root cause analysis
2. Specific fix recommendations
3. Updated code with the fix applied
4. Confidence score (0-100%)
5. Alternative approaches

Return JSON with this structure:
{
  "root_cause": "Detailed explanation",
  "automated_fix": {
    "original_code": "The failing line",
    "fixed_code": "The corrected line",
    "explanation": "Why this fixes it"
  },
  "confidence_score": 85,
  "validation_steps": ["Step 1", "Step 2"],
  "alternatives": ["Alternative 1", "Alternative 2"]
}"""

        user_prompt = f"""Test Failure Analysis:

Test ID: {test_id}
Error: {error_msg}
Category: {category}

Test Script:
```typescript
{script_code[:2000]}  # Truncate for token limit
```

Analyze this failure and provide healing suggestions."""

        result = self.llm.complete_json(
            system=system_prompt, user=user_prompt, max_tokens=2048, temperature=0.3
        )

        # Process LLM result
        if result and isinstance(result, dict):
            return {
                "test_id": test_id,
                "failure_category": category,
                "root_cause": result.get("root_cause", "Unknown"),
                "confidence_score": result.get("confidence_score", 50),
                "automated_fix": result.get("automated_fix", {}),
                "validation_steps": result.get("validation_steps", []),
                "alternatives": result.get("alternatives", []),
            }

        # Fallback if LLM doesn't return proper format
        return self._generate_fallback_suggestion(test_id, error_msg, category)

    def _categorize_failure(self, error_msg: str) -> str:
        """Categorize failure based on error message."""
        error_lower = error_msg.lower()

        if "selector" in error_lower or "not found" in error_lower:
            return "selector_issue"
        elif "timeout" in error_lower or "wait" in error_lower:
            return "timing_issue"
        elif "expected" in error_lower or "assert" in error_lower:
            return "assertion_failure"
        elif "network" in error_lower or "connection" in error_lower:
            return "environmental_issue"
        else:
            return "unknown"

    def _find_test_script(self, run_id: str, test_id: str) -> Path | None:
        """Find the test script file for a given test ID."""
        playwright_dir = self.root_dir / "runs" / run_id / "playwright_tests"
        if not playwright_dir.exists():
            return None

        # Extract filename from test_id (e.g., "story-001.spec.ts::test-1" -> "story-001.spec.ts")
        if "::" in test_id:
            filename = test_id.split("::")[0]
            script_file = playwright_dir / filename
            if script_file.exists():
                return script_file

        return None

    def _generate_fallback_suggestion(
        self, test_id: str, error_msg: str, category: str
    ) -> dict[str, Any]:
        """Generate fallback healing suggestion if LLM fails."""
        suggestions_map = {
            "selector_issue": {
                "root_cause": "Element selector may have changed or element not rendered",
                "fix": "Use more robust selector (data-testid, role-based)",
                "confidence": 70,
            },
            "timing_issue": {
                "root_cause": "Element not ready or action too fast",
                "fix": "Add explicit wait or waitForLoadState",
                "confidence": 80,
            },
            "assertion_failure": {
                "root_cause": "Expected value doesn't match actual value",
                "fix": "Verify test data and expected results",
                "confidence": 60,
            },
            "environmental_issue": {
                "root_cause": "External dependency or environment setup issue",
                "fix": "Check API endpoints, database, and service health",
                "confidence": 40,
            },
        }

        suggestion = suggestions_map.get(category, {
            "root_cause": "Unknown failure",
            "fix": "Manual investigation required",
            "confidence": 30,
        })

        return {
            "test_id": test_id,
            "failure_category": category,
            "root_cause": f"{suggestion['root_cause']}. Error: {error_msg}",
            "confidence_score": suggestion["confidence"],
            "automated_fix": {
                "explanation": suggestion["fix"],
                "original_code": "// Code inspection needed",
                "fixed_code": "// Apply suggested fix",
            },
            "validation_steps": [
                "Review test script",
                "Verify element selectors",
                "Re-run test after fix",
            ],
            "alternatives": [
                "Add screenshot on failure for debugging",
                "Increase timeout values",
                "Use different selector strategy",
            ],
        }

    def _save_healing_report(
        self, run_id: str, healing_suggestions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Save healing report to JSON file."""
        runs_dir = self.root_dir / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)

        # Count auto-fixable (confidence >= 80%)
        auto_fixable = sum(
            1 for s in healing_suggestions if s["confidence_score"] >= 80
        )
        manual_review = len(healing_suggestions) - auto_fixable

        result = {
            "run_id": run_id,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "failures_analyzed": len(healing_suggestions),
            "auto_fixable": auto_fixable,
            "manual_review_needed": manual_review,
            "healing_suggestions": healing_suggestions,
        }

        output_file = runs_dir / "test_healing.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved healing report to {output_file}")
        return result
