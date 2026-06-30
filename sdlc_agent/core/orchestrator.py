"""Pipeline orchestrator.

Wires the six stages together and enforces the single human approval gate
between Stage 2 and Stage 3. If Stage 4 fails, Stage 3 is retried up to
`max_remediation_attempts` times (Phase 1 keeps the remediation loop trivial —
the stub Stage 3 produces deterministic output, so a real fail-loop would
require Stage 3 to consume review findings; this is wired in for Phase 2/3).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Callable

from ..harness import ensure_harness
from ..harness import get_harness, Severity
from ..integrations import (
    ClaudeClient,
    MockConfluenceClient,
    MockGitHubClient,
    GitHubRestClient,
    MockJiraClient,
    JiraClient,
)
from .github_config import should_use_real_github, should_post_review_comments
from .models import PipelineResult, StoryBacklog
from ..stages import (
    stage1_requirement,
    stage2_stories,
    stage3_code,
    stage4_review,
    stage5_tests,
    stage6_deploy,
)


ApprovalCallback = Callable[[StoryBacklog], bool]


def _auto_approve(_: StoryBacklog) -> bool:
    return True


class Orchestrator:
    def __init__(
        self,
        *,
        confluence: MockConfluenceClient | None = None,
        jira: object = None,
        github: MockGitHubClient | GitHubRestClient | None = None,
        claude: ClaudeClient | None = None,
        max_remediation_attempts: int = 2,
        use_harness: bool = True,
        use_real_github: bool | None = None,
    ) -> None:
        # Ensure harness is initialized with hooks (if enabled)
        if use_harness:
            ensure_harness()

        self.confluence = confluence or MockConfluenceClient()
        # Prefer real JiraClient if env vars are set, else fallback to mock
        if jira is not None:
            self.jira = jira
        elif all(os.environ.get(k) for k in ("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY")):
            from .integrations import JiraClient
            self.jira = JiraClient(
                server_url=os.environ["JIRA_URL"],
                email=os.environ["JIRA_EMAIL"],
                api_token=os.environ["JIRA_API_TOKEN"],
                project_key=os.environ["JIRA_PROJECT_KEY"],
                auto_transition=os.environ.get("JIRA_AUTO_STATUS", "Ready for QA")
            )
        else:
            self.jira = MockJiraClient()

        # Determine GitHub client to use
        self.use_real_github = use_real_github if use_real_github is not None else should_use_real_github()
        if github is not None:
            self.github = github
        elif self.use_real_github:
            self.github = GitHubRestClient()
        else:
            self.github = MockGitHubClient()

        self.claude = claude or ClaudeClient()
        self.max_remediation_attempts = max_remediation_attempts
        self.harness = get_harness() if use_harness else None

    def run(
        self,
        source_ref: str,
        *,
        approver: str = "auto",
        approval: ApprovalCallback = _auto_approve,
        inject_defect: bool = False,
    ) -> PipelineResult:
        """Drive the six-stage pipeline end-to-end.

        Args:
            source_ref: BRD path, Confluence URL, or raw text.
            approver: Name recorded on the backlog when approved.
            approval: Callback invoked at the Stage 2/3 gate.
            inject_defect: Demo aid. The first Stage 3 invocation emits a
                deliberately faulty PR; Stage 4 must catch it; the
                remediation rerun produces a clean PR.
        """
        if self.harness:
            self.harness.log(Severity.INFO, f"Pipeline started: {source_ref}")

        # Stage 1
        if self.harness:
            self.harness.transition_to("requirement", "Winston")
            with self.harness.tool_span("stage1_requirement"):
                brief = stage1_requirement.run(
                    source_ref, confluence=self.confluence, claude=self.claude
                )
        else:
            brief = stage1_requirement.run(
                source_ref, confluence=self.confluence, claude=self.claude
            )

        # Stage 2
        if self.harness:
            self.harness.transition_to("stories", "Priya")
            with self.harness.tool_span("stage2_stories"):
                backlog = stage2_stories.run(brief, jira=self.jira, claude=self.claude)
        else:
            backlog = stage2_stories.run(brief, jira=self.jira, claude=self.claude)

        # Human approval gate
        if not approval(backlog):
            if self.harness:
                self.harness.log(Severity.WARN, "Backlog not approved - halted at PO gate")
            return PipelineResult(brief=brief, backlog=backlog)
        backlog.approved = True
        backlog.approver = approver
        backlog.approved_at = datetime.now(timezone.utc)

        if self.harness:
            self.harness.log(Severity.INFO, f"Backlog approved by {approver}")

        # Stages 3 + 4 (with bounded remediation loop)
        if self.harness:
            self.harness.transition_to("code", "Amelia")
            with self.harness.tool_span("stage3_code"):
                pr = stage3_code.run(
                    backlog,
                    github=self.github,
                    claude=self.claude,
                    inject_defect=inject_defect,
                    use_real_github=self.use_real_github,
                )
        else:
            pr = stage3_code.run(
                backlog,
                github=self.github,
                claude=self.claude,
                inject_defect=inject_defect,
                use_real_github=self.use_real_github,
            )

        post_comments = should_post_review_comments()
        github_for_review = self.github if isinstance(self.github, GitHubRestClient) else None

        if self.harness:
            self.harness.transition_to("review", "Devon")
            with self.harness.tool_span("stage4_review"):
                review = stage4_review.run(
                    pr,
                    claude=self.claude,
                    github=github_for_review,
                    post_comments=post_comments,
                )
        else:
            review = stage4_review.run(
                pr,
                claude=self.claude,
                github=github_for_review,
                post_comments=post_comments,
            )

        attempts = 0
        while review.verdict == "fail" and attempts < self.max_remediation_attempts:
            attempts += 1
            if self.harness:
                self.harness.log(
                    Severity.WARN,
                    f"Review failed (attempt {attempts}/{self.max_remediation_attempts})"
                )
                with self.harness.tool_span(f"stage3_code_remediation_{attempts}"):
                    pr = stage3_code.run(
                        backlog,
                        github=self.github,
                        claude=self.claude,
                        inject_defect=False,
                        use_real_github=self.use_real_github,
                    )
                with self.harness.tool_span(f"stage4_review_retry_{attempts}"):
                    review = stage4_review.run(
                        pr,
                        claude=self.claude,
                        github=github_for_review,
                        post_comments=post_comments,
                    )
            else:
                pr = stage3_code.run(
                    backlog,
                    github=self.github,
                    claude=self.claude,
                    inject_defect=False,
                    use_real_github=self.use_real_github,
                )
                review = stage4_review.run(
                    pr,
                    claude=self.claude,
                    github=github_for_review,
                    post_comments=post_comments,
                )

        # Stage 5
        if self.harness:
            self.harness.transition_to("tests", "Quinn")
            with self.harness.tool_span("stage5_tests"):
                tests = stage5_tests.run(
                    pr, backlog, github=self.github, claude=self.claude
                )
        else:
            tests = stage5_tests.run(
                pr, backlog, github=self.github, claude=self.claude
            )

        # Re-run review now that tests are attached so the coverage gate clears.
        if self.harness:
            with self.harness.tool_span("stage4_review_final"):
                review = stage4_review.run(pr, claude=self.claude)
        else:
            review = stage4_review.run(pr, claude=self.claude)

        # Stage 6
        if self.harness:
            self.harness.transition_to("deploy", "Marcus")
            with self.harness.tool_span("stage6_deploy"):
                decision = stage6_deploy.run(
                    pr, review, tests, backlog, github=self.github, claude=self.claude
                )
            self.harness.log(
                Severity.INFO,
                f"Pipeline complete: {'GO' if decision.go else 'NO-GO'}"
            )
        else:
            decision = stage6_deploy.run(
                pr, review, tests, backlog, github=self.github, claude=self.claude
            )

        return PipelineResult(
            brief=brief,
            backlog=backlog,
            pull_request=pr,
            review=review,
            tests=tests,
            decision=decision,
        )
