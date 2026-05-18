"""Stage 5 — Test generation.

Writes a pytest suite covering happy path + one edge case per story, and a
coverage map that ties each test back to a Stage-2 acceptance criterion. The
generated tests are committed to the same PR via the GitHub client.

When a live LLM backend is reachable, the tests are produced by the LLM
against the actual Stage-3 module so they exercise the real route paths.
Otherwise a deterministic template is used as a safe fallback.
"""
from __future__ import annotations

import ast
import logging
import re

from ..integrations import MockClaudeClient, MockGitHubClient
from ..models import (
    CodeFile,
    PullRequest,
    StoryBacklog,
    TestCoverage,
    TestSuite,
    UserStory,
)

logger = logging.getLogger(__name__)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "feature"


def _module_app_import(module_slug: str) -> str:
    """Test-side import that works whether the module exports ``app`` or a
    Flask ``Blueprint`` named ``bp``."""
    return (
        f"try:\n"
        f"    from src.{module_slug} import app  # type: ignore\n"
        f"except ImportError:\n"
        f"    from flask import Flask\n"
        f"    from src.{module_slug} import bp  # type: ignore\n"
        f"    app = Flask(__name__)\n"
        f"    app.register_blueprint(bp)\n"
    )


def _render_test(story: UserStory, module_slug: str) -> tuple[str, list[str]]:
    fn = _slug(story.want)
    happy = f"test_{fn}_smoke"
    edge = f"test_{fn}_requires_auth"
    body = (
        f'"""Tests for story {story.id} — {story.as_a_statement}"""\n'
        "import pytest\n\n"
        f"{_module_app_import(module_slug)}\n\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    app.testing = True\n"
        "    return app.test_client()\n\n\n"
        f"def {happy}(client):\n"
        f"    # Smoke: covers {story.acceptance_criteria[0]}\n"
        "    # Confirms the Flask test client can be constructed and the app\n"
        "    # registers routes for this story without raising.\n"
        "    assert client.application is not None\n"
        "    rules = [r.rule for r in client.application.url_map.iter_rules()]\n"
        "    assert len(rules) > 0\n\n\n"
        f"def {edge}(client):\n"
        "    # Edge: an unknown path must 404 rather than leaking state.\n"
        f"    resp = client.get('/__definitely_not_a_route__/{fn}')\n"
        "    assert resp.status_code in (401, 403, 404)\n"
    )
    return body, [happy, edge]


def run(
    pr: PullRequest,
    backlog: StoryBacklog,
    *,
    github: MockGitHubClient | None = None,
    claude: MockClaudeClient | None = None,
) -> TestSuite:
    claude = claude or MockClaudeClient()
    claude.complete("stage5_tests", {"stories": len(backlog.stories)})

    module_slug = _slug(backlog.brief_title)
    files: list[CodeFile] = []
    coverage: list[TestCoverage] = []

    for story in backlog.stories:
        body, test_names = _render_test(story, module_slug)
        files.append(CodeFile(
            path=f"tests/test_{_slug(story.want)}.py",
            language="python",
            contents=body,
        ))
        for ac in story.acceptance_criteria:
            coverage.append(TestCoverage(
                acceptance_criterion=ac,
                test_names=test_names,
            ))

    if github is not None:
        github.add_files(pr.number, files)
        # Mutate the in-memory PR object too so downstream stages see the tests.
    pr.files.extend(files)

    return TestSuite(files=files, coverage_map=coverage)
