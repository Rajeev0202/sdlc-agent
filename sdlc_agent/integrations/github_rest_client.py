"""Real GitHub client using GitHub REST API.

This client integrates directly with the GitHub REST API to:
1. Create pull requests with proper titles and descriptions
2. Post review comments on PR files
3. Update PR status and labels

Requires GITHUB_TOKEN environment variable with appropriate permissions:
- repo (full control of private repositories)
- pull_requests (read/write)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

import requests

from ..core.models import CodeFile, PullRequest, ReviewFinding, ReviewReport

logger = logging.getLogger(__name__)


class GitHubRestClient:
    """GitHub client that uses REST API for PR operations."""

    BASE_URL = "https://api.github.com"

    def __init__(self, repo: str | None = None, token: str | None = None) -> None:
        """Initialize GitHub REST API client.

        Args:
            repo: Repository in format "owner/repo". If None, inferred from git remote.
            token: GitHub personal access token. If None, read from GITHUB_TOKEN env var.

        Raises:
            ValueError: If token is not provided and GITHUB_TOKEN env var is not set.
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise ValueError(
                "GitHub token required. Set GITHUB_TOKEN environment variable or pass token parameter."
            )

        self.repo = repo or self._get_repo_from_remote()
        self.owner, self.repo_name = self.repo.split("/")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SDLC-Agent/1.0",
        })

        self._pr_cache: dict[int, PullRequest] = {}
        logger.info("GitHubRestClient initialized for repo: %s", self.repo)

    def _get_repo_from_remote(self) -> str:
        """Extract repository owner/name from git remote."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            url = result.stdout.strip()
            # Parse https://github.com/owner/repo.git or git@github.com:owner/repo.git
            if "github.com" in url:
                parts = url.replace(".git", "").replace(":", "/").split("/")
                return f"{parts[-2]}/{parts[-1]}"
            raise ValueError(f"Could not parse GitHub repo from URL: {url}")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as exc:
            logger.warning("Could not infer repo from git remote: %s", exc)
            raise ValueError("Could not determine repository from git remote") from exc

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a request to GitHub REST API.

        Args:
            method: HTTP method (GET, POST, PATCH, etc.)
            endpoint: API endpoint path (e.g., "/repos/{owner}/{repo}/pulls")
            data: JSON payload for POST/PATCH requests
            params: Query parameters

        Returns:
            Parsed JSON response

        Raises:
            RuntimeError: If the API request fails
        """
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as exc:
            error_msg = f"GitHub API error: {exc.response.status_code}"
            try:
                error_detail = exc.response.json()
                error_msg += f" - {error_detail.get('message', '')}"
            except Exception:
                pass
            logger.error("%s: %s", error_msg, endpoint)
            raise RuntimeError(error_msg) from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Request failed: %s", exc)
            raise RuntimeError(f"GitHub API request failed: {exc}") from exc

    def open_pull_request(
        self,
        branch: str,
        title: str,
        body: str,
        files: list[CodeFile],
        story_ids: list[str],
    ) -> PullRequest:
        """Create a pull request on GitHub.

        Args:
            branch: Feature branch name
            title: PR title
            body: PR description (supports markdown)
            files: List of code files in the PR
            story_ids: Jira story IDs referenced in this PR

        Returns:
            PullRequest object with PR number and metadata
        """
        logger.info("Creating PR: branch=%s, title=%s", branch, title)

        # Ensure branch is pushed to remote (if not already)
        # Stage 3 should have already pushed, but this is a safety check
        try:
            self._push_branch(branch)
        except RuntimeError as exc:
            # Branch might already be pushed, which is fine
            if "up-to-date" not in str(exc).lower():
                logger.warning("Could not push branch (may already exist): %s", exc)

        # Build enhanced PR body with story references
        enhanced_body = self._build_pr_body(body, story_ids, files)

        # Check if PR already exists for this branch
        existing_pr = self._find_existing_pr(branch)
        if existing_pr:
            logger.info("PR already exists for branch %s: #%d", branch, existing_pr["number"])
            return self._convert_to_pr_model(existing_pr, files, story_ids)

        # Create PR via REST API
        try:
            pr_data = self._make_request(
                method="POST",
                endpoint=f"/repos/{self.owner}/{self.repo_name}/pulls",
                data={
                    "title": title,
                    "body": enhanced_body,
                    "head": branch,
                    "base": "main",
                    "draft": True,
                },
            )

            logger.info("Created PR #%d: %s", pr_data["number"], pr_data["html_url"])

            pr = self._convert_to_pr_model(pr_data, files, story_ids)
            self._pr_cache[pr.number] = pr
            return pr

        except RuntimeError as exc:
            logger.error("Failed to create PR: %s", exc)
            raise

    def _push_branch(self, branch: str) -> None:
        """Push branch to remote origin."""
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", branch],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            logger.info("Pushed branch %s to origin", branch)
        except subprocess.CalledProcessError as exc:
            # Branch might already be pushed
            if "already exists" not in exc.stderr and "up-to-date" not in exc.stderr:
                logger.warning("Failed to push branch %s: %s", branch, exc.stderr)

    def _build_pr_body(
        self, body: str, story_ids: list[str], files: list[CodeFile]
    ) -> str:
        """Build enhanced PR description with metadata."""
        sections = [body, ""]

        if story_ids:
            sections.append("## 📋 Related Stories")
            sections.extend(f"- {story_id}" for story_id in story_ids)
            sections.append("")

        sections.append("## 📁 Changed Files")
        sections.extend(f"- `{f.path}` ({f.language})" for f in files)
        sections.append("")

        sections.append("---")
        sections.append("🤖 *Generated by SDLC Agent (Stage 3) - Claude Code*")

        return "\n".join(sections)

    def _find_existing_pr(self, branch: str) -> dict[str, Any] | None:
        """Find existing PR for a branch.

        Returns:
            PR data dict if found, None otherwise
        """
        try:
            prs = self._make_request(
                method="GET",
                endpoint=f"/repos/{self.owner}/{self.repo_name}/pulls",
                params={"head": f"{self.owner}:{branch}", "state": "open"},
            )
            return prs[0] if prs else None
        except (RuntimeError, IndexError, KeyError):
            return None

    def _convert_to_pr_model(
        self,
        pr_data: dict[str, Any],
        files: list[CodeFile],
        story_ids: list[str],
    ) -> PullRequest:
        """Convert GitHub API PR data to PullRequest model."""
        return PullRequest(
            number=pr_data["number"],
            branch=pr_data["head"]["ref"],
            title=pr_data["title"],
            body=pr_data["body"] or "",
            files=list(files),
            story_ids=list(story_ids),
            state="draft" if pr_data.get("draft", False) else pr_data["state"],
        )

    def post_review_comments(
        self, pr_number: int, review_report: ReviewReport
    ) -> None:
        """Post review findings as comments on the PR.

        Args:
            pr_number: Pull request number
            review_report: Review report with findings
        """
        logger.info(
            "Posting %d review comments on PR #%d",
            len(review_report.findings),
            pr_number,
        )

        if not review_report.findings:
            self._post_approval_comment(pr_number)
            return

        # Get PR details to obtain the commit SHA
        pr_data = self._make_request(
            method="GET",
            endpoint=f"/repos/{self.owner}/{self.repo_name}/pulls/{pr_number}",
        )
        commit_sha = pr_data["head"]["sha"]

        # Prepare review comments
        comments = []
        general_comments = []

        for finding in review_report.findings:
            if finding.line is not None:
                # Inline comment
                comments.append(self._format_review_comment(finding, commit_sha))
            else:
                # General comment (no specific line)
                general_comments.append(finding)

        # Post review with inline comments
        if comments:
            try:
                self._make_request(
                    method="POST",
                    endpoint=f"/repos/{self.owner}/{self.repo_name}/pulls/{pr_number}/reviews",
                    data={
                        "commit_id": commit_sha,
                        "body": self._format_review_summary(review_report),
                        "event": "COMMENT",  # Don't approve or request changes, just comment
                        "comments": comments,
                    },
                )
                logger.info("Posted %d inline review comments on PR #%d", len(comments), pr_number)
            except RuntimeError as exc:
                logger.warning("Failed to post inline comments: %s", exc)
                # Fall back to regular comments
                self._post_fallback_comments(pr_number, review_report.findings)

        # Post general comments separately
        for finding in general_comments:
            self._post_issue_comment(pr_number, self._format_finding(finding))

        # Post summary comment
        self._post_summary_comment(pr_number, review_report)

    def _format_review_comment(
        self, finding: ReviewFinding, commit_sha: str
    ) -> dict[str, Any]:
        """Format a finding as a GitHub review comment."""
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
            "info": "ℹ️",
        }
        emoji = severity_emoji.get(finding.severity.value, "•")

        body = (
            f"{emoji} **{finding.severity.value.upper()}** [{finding.category}]\n\n"
            f"{finding.message}\n\n"
            f"---\n*SDLC Agent - Stage 4 Review*"
        )

        return {
            "path": finding.file,
            "line": finding.line,
            "body": body,
        }

    def _format_finding(self, finding: ReviewFinding) -> str:
        """Format a finding as markdown text."""
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
            "info": "ℹ️",
        }
        emoji = severity_emoji.get(finding.severity.value, "•")

        location = f"{finding.file}:{finding.line}" if finding.line else finding.file

        return (
            f"{emoji} **{finding.severity.value.upper()}** [{finding.category}]\n\n"
            f"**Location:** `{location}`\n\n"
            f"{finding.message}\n\n"
            f"---\n*SDLC Agent - Stage 4 Review*"
        )

    def _format_review_summary(self, review_report: ReviewReport) -> str:
        """Format the review report summary."""
        verdict_emoji = "✅" if review_report.verdict == "pass" else "❌"

        lines = [
            f"## {verdict_emoji} Code Review Summary",
            "",
            f"**Verdict:** {review_report.verdict.upper()}",
            f"**Total Findings:** {len(review_report.findings)}",
        ]

        if review_report.verdict == "fail":
            blocking = [
                f for f in review_report.findings
                if f.severity.value in ("critical", "high")
            ]
            lines.extend([
                "",
                f"⚠️ **{len(blocking)} blocking issue(s)** must be resolved before merging.",
            ])

        return "\n".join(lines)

    def _post_fallback_comments(
        self, pr_number: int, findings: list[ReviewFinding]
    ) -> None:
        """Post findings as regular issue comments when review API fails."""
        for finding in findings:
            self._post_issue_comment(pr_number, self._format_finding(finding))

    def _post_issue_comment(self, pr_number: int, body: str) -> None:
        """Post a regular comment on the PR."""
        try:
            self._make_request(
                method="POST",
                endpoint=f"/repos/{self.owner}/{self.repo_name}/issues/{pr_number}/comments",
                data={"body": body},
            )
            logger.info("Posted comment on PR #%d", pr_number)
        except RuntimeError as exc:
            logger.warning("Failed to post comment on PR #%d: %s", pr_number, exc)

    def _post_summary_comment(
        self, pr_number: int, review_report: ReviewReport
    ) -> None:
        """Post a summary review comment."""
        from collections import Counter

        severity_counts = Counter(f.severity.value for f in review_report.findings)
        category_counts = Counter(f.category for f in review_report.findings)

        verdict_emoji = "✅" if review_report.verdict == "pass" else "❌"

        summary_lines = [
            f"## {verdict_emoji} Code Review Summary",
            "",
            f"**Verdict:** {review_report.verdict.upper()}",
            "",
            "### 📊 Findings by Severity",
        ]

        for severity in ["critical", "high", "medium", "low", "info"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "ℹ️"}[severity]
                summary_lines.append(f"- {emoji} **{severity.title()}**: {count}")

        summary_lines.extend([
            "",
            "### 🏷️ Findings by Category",
        ])

        for category, count in category_counts.most_common():
            summary_lines.append(f"- **{category.title()}**: {count}")

        if review_report.verdict == "fail":
            blocking = [
                f for f in review_report.findings
                if f.severity.value in ("critical", "high")
            ]
            summary_lines.extend([
                "",
                f"### ⚠️ Blocking Issues ({len(blocking)})",
                "",
                "These issues must be resolved before merging:",
                "",
            ])
            for finding in blocking:
                summary_lines.append(
                    f"- `{finding.file}:{finding.line or '?'}` - {finding.message}"
                )

        summary_lines.extend([
            "",
            "---",
            "*🤖 Generated by SDLC Agent - Stage 4 Review*",
        ])

        comment = "\n".join(summary_lines)
        self._post_issue_comment(pr_number, comment)

    def _post_approval_comment(self, pr_number: int) -> None:
        """Post an approval comment when no issues found."""
        comment = (
            "## ✅ Code Review Passed\n\n"
            "No issues found! The code meets all review criteria:\n\n"
            "- ✅ Security standards\n"
            "- ✅ Coding conventions\n"
            "- ✅ Logic correctness\n"
            "- ✅ Test coverage\n\n"
            "Ready to proceed to testing phase.\n\n"
            "---\n"
            "*🤖 Generated by SDLC Agent - Stage 4 Review*"
        )
        self._post_issue_comment(pr_number, comment)

    def mark_ready_for_review(self, pr_number: int) -> None:
        """Mark PR as ready for review (remove draft status)."""
        try:
            self._make_request(
                method="PATCH",
                endpoint=f"/repos/{self.owner}/{self.repo_name}/pulls/{pr_number}",
                data={"draft": False},
            )
            logger.info("Marked PR #%d as ready for review", pr_number)

            if pr_number in self._pr_cache:
                self._pr_cache[pr_number].state = "open"  # type: ignore[assignment]
        except RuntimeError as exc:
            logger.warning("Failed to mark PR #%d as ready: %s", pr_number, exc)

    def add_labels(self, pr_number: int, labels: list[str]) -> None:
        """Add labels to a PR."""
        if not labels:
            return

        try:
            self._make_request(
                method="POST",
                endpoint=f"/repos/{self.owner}/{self.repo_name}/issues/{pr_number}/labels",
                data={"labels": labels},
            )
            logger.info("Added labels to PR #%d: %s", pr_number, labels)
        except RuntimeError as exc:
            logger.warning("Failed to add labels to PR #%d: %s", pr_number, exc)

    def get_pr_files(self, pr_number: int) -> list[CodeFile]:
        """Fetch the actual files from a GitHub PR.

        Args:
            pr_number: Pull request number

        Returns:
            List of CodeFile objects with actual content from GitHub
        """
        from pathlib import Path

        logger.info("Fetching files from PR #%d", pr_number)

        try:
            # Get list of changed files
            files_data = self._make_request(
                method="GET",
                endpoint=f"/repos/{self.owner}/{self.repo_name}/pulls/{pr_number}/files",
            )

            code_files: list[CodeFile] = []

            for file_info in files_data:
                filename = file_info["filename"]
                status = file_info["status"]  # added, modified, removed, renamed

                # Skip deleted files
                if status == "removed":
                    logger.info("Skipping removed file: %s", filename)
                    continue

                # Get file contents from the PR's head commit
                # GitHub API provides raw_url for the file content
                if "raw_url" in file_info:
                    try:
                        import requests
                        response = requests.get(
                            file_info["raw_url"],
                            headers={"Authorization": f"token {self.token}"},
                            timeout=10,
                        )
                        response.raise_for_status()
                        contents = response.text
                    except Exception as exc:
                        logger.warning("Could not fetch %s: %s", filename, exc)
                        continue
                else:
                    # Fall back to reading from local filesystem if file was just committed
                    try:
                        file_path = Path.cwd() / filename
                        if file_path.exists():
                            contents = file_path.read_text(encoding="utf-8")
                        else:
                            logger.warning("File not found: %s", filename)
                            continue
                    except Exception as exc:
                        logger.warning("Could not read %s: %s", filename, exc)
                        continue

                # Determine language from file extension
                language = self._detect_language(filename)

                code_files.append(
                    CodeFile(path=filename, language=language, contents=contents)
                )

            logger.info("Fetched %d files from PR #%d", len(code_files), pr_number)
            return code_files

        except RuntimeError as exc:
            logger.error("Failed to fetch PR files: %s", exc)
            return []

    def _detect_language(self, filename: str) -> str:
        """Detect programming language from filename."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        lang_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "jsx": "javascript",
            "java": "java",
            "go": "go",
            "rs": "rust",
            "c": "c",
            "cpp": "cpp",
            "h": "c",
            "hpp": "cpp",
            "cs": "csharp",
            "rb": "ruby",
            "php": "php",
            "sh": "bash",
            "sql": "sql",
            "yaml": "yaml",
            "yml": "yaml",
            "json": "json",
            "xml": "xml",
            "html": "html",
            "css": "css",
            "md": "markdown",
        }
        return lang_map.get(ext, "text")
