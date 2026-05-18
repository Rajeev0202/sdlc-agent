"""Mocked Jira client — creates issues for the generated user stories."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import UserStory


@dataclass
class JiraIssue:
    key: str
    summary: str
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)


class MockJiraClient:
    def __init__(self, project_key: str = "NW") -> None:
        self.project_key = project_key
        self._counter = 0
        self.issues: dict[str, JiraIssue] = {}

    def create_story(self, story: UserStory) -> JiraIssue:
        self._counter += 1
        key = f"{self.project_key}-{1000 + self._counter}"
        issue = JiraIssue(
            key=key,
            summary=story.want,
            description=story.as_a_statement,
            acceptance_criteria=list(story.acceptance_criteria),
        )
        self.issues[key] = issue
        return issue
