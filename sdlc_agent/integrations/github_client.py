"""Mocked GitHub client — opens draft PRs and appends commits."""
from __future__ import annotations

from ..models import CodeFile, PullRequest


class MockGitHubClient:
    def __init__(self, repo: str = "natwest/payments-service") -> None:
        self.repo = repo
        self._pr_counter = 0
        self.pull_requests: dict[int, PullRequest] = {}

    def open_pull_request(
        self,
        branch: str,
        title: str,
        body: str,
        files: list[CodeFile],
        story_ids: list[str],
    ) -> PullRequest:
        self._pr_counter += 1
        pr = PullRequest(
            number=self._pr_counter,
            branch=branch,
            title=title,
            body=body,
            files=list(files),
            story_ids=list(story_ids),
            state="draft",
        )
        self.pull_requests[pr.number] = pr
        return pr

    def add_files(self, pr_number: int, files: list[CodeFile]) -> PullRequest:
        pr = self.pull_requests[pr_number]
        existing = {f.path: f for f in pr.files}
        for f in files:
            existing[f.path] = f
        pr.files = list(existing.values())
        return pr

    def set_state(
        self, pr_number: int, state: str
    ) -> PullRequest:
        pr = self.pull_requests[pr_number]
        pr.state = state  # type: ignore[assignment]
        return pr
