"""Git operations for committing and pushing code changes.

Handles file writing, git add, commit, and push operations for the SDLC pipeline.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from ..core.models import CodeFile, StoryBacklog

logger = logging.getLogger(__name__)


class GitOperations:
    """Git operations client for file management and version control."""

    def __init__(self, repo_root: Path | None = None) -> None:
        """Initialize git operations.

        Args:
            repo_root: Root directory of the git repository. If None, uses current directory.
        """
        self.repo_root = repo_root or Path.cwd()
        logger.info("GitOperations initialized at: %s", self.repo_root)

    def _run_git_command(
        self, args: list[str], check: bool = True, timeout: int = 30
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command.

        Args:
            args: Git command arguments (e.g., ['status', '-s'])
            check: Whether to raise on non-zero exit code
            timeout: Command timeout in seconds

        Returns:
            CompletedProcess with command results

        Raises:
            RuntimeError: If command fails and check=True
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=check,
                timeout=timeout,
            )
            return result
        except subprocess.CalledProcessError as exc:
            logger.error("Git command failed: git %s", " ".join(args))
            logger.error("Error: %s", exc.stderr)
            raise RuntimeError(f"Git command failed: {exc.stderr}") from exc
        except subprocess.TimeoutExpired as exc:
            logger.error("Git command timed out: git %s", " ".join(args))
            raise RuntimeError(f"Git command timed out after {timeout}s") from exc

    def get_current_branch(self) -> str:
        """Get the current git branch name.

        Returns:
            Current branch name
        """
        result = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        return result.stdout.strip()

    def create_branch(self, branch_name: str, from_branch: str = "feature/sdlc-agent") -> None:
        """Create and checkout a new git branch.

        Args:
            branch_name: Name of the branch to create
            from_branch: Base branch to branch from (default: main)
        """
        logger.info("Creating branch %s from %s", branch_name, from_branch)

        # Check if branch already exists
        result = self._run_git_command(
            ["rev-parse", "--verify", branch_name], check=False
        )
        if result.returncode == 0:
            logger.info("Branch %s already exists, checking it out", branch_name)
            try:
                self._run_git_command(["checkout", branch_name])
                return
            except RuntimeError:
                logger.warning("Could not checkout existing branch, will recreate it")
                # Branch exists but can't checkout - might have uncommitted changes
                # Just create the branch from current location
                return

        # Determine the actual default branch (might be main or master)
        actual_base = self._get_default_branch(from_branch)

        # Check if we're already on the base branch
        current_branch = self.get_current_branch()
        if current_branch != actual_base:
            # Need to switch to base branch
            try:
                # Stash any uncommitted changes
                stash_result = self._run_git_command(["stash"], check=False)
                had_stashed = "No local changes" not in stash_result.stdout

                # Checkout base branch
                self._run_git_command(["checkout", actual_base])

                # Pull latest changes
                try:
                    self._run_git_command(["pull", "origin", actual_base], check=False)
                except RuntimeError:
                    logger.warning("Could not pull latest changes from %s", actual_base)

                # Create new branch
                self._run_git_command(["checkout", "-b", branch_name])

                # Pop stash if we stashed
                if had_stashed:
                    self._run_git_command(["stash", "pop"], check=False)

            except RuntimeError as exc:
                logger.error("Failed to switch branches: %s", exc)
                # Fall back to creating branch from current location
                logger.info("Creating branch from current location instead")
                self._run_git_command(["checkout", "-b", branch_name])
        else:
            # Already on base branch, just create new branch
            self._run_git_command(["checkout", "-b", branch_name])

        logger.info("Created and checked out branch: %s", branch_name)

    def _get_default_branch(self, preferred: str = "main") -> str:
        """Get the actual default branch (main or master).

        Args:
            preferred: Preferred branch name to try first

        Returns:
            Name of the default branch that exists
        """
        # Try preferred branch first
        result = self._run_git_command(
            ["rev-parse", "--verify", preferred], check=False
        )
        if result.returncode == 0:
            return preferred

        # Try alternate common names
        alternates = ["master", "develop"] if preferred == "main" else ["main", "develop"]
        for branch in alternates:
            result = self._run_git_command(
                ["rev-parse", "--verify", branch], check=False
            )
            if result.returncode == 0:
                logger.info("Using %s as base branch (preferred %s not found)", branch, preferred)
                return branch

        # Fall back to current branch
        current = self.get_current_branch()
        logger.warning("Neither %s nor alternates found, using current branch: %s", preferred, current)
        return current

    def write_files(self, files: list[CodeFile]) -> list[Path]:
        """Write code files to disk.

        Args:
            files: List of CodeFile objects to write

        Returns:
            List of Path objects for written files
        """
        written_paths: list[Path] = []

        for code_file in files:
            file_path = self.repo_root / code_file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info("Writing file: %s (%d bytes)", code_file.path, len(code_file.contents))
            file_path.write_text(code_file.contents, encoding="utf-8")
            written_paths.append(file_path)

        return written_paths

    def stage_files(self, file_paths: list[Path]) -> None:
        """Stage files for commit.

        Args:
            file_paths: List of file paths to stage
        """
        for file_path in file_paths:
            relative_path = file_path.relative_to(self.repo_root)
            logger.info("Staging file: %s", relative_path)
            self._run_git_command(["add", str(relative_path)])

    def commit_changes(
        self, message: str, backlog: StoryBacklog | None = None
    ) -> str:
        """Commit staged changes.

        Args:
            message: Commit message
            backlog: Optional backlog to extract story IDs from

        Returns:
            Commit SHA

        Raises:
            RuntimeError: If commit fails
        """
        # Ensure git user is configured
        self._ensure_git_user_configured()

        # Build commit message with story references
        commit_msg_lines = [message, ""]

        if backlog:
            commit_msg_lines.extend([
                "Implements user stories:",
                *(f"- {s.id}: {s.want}" for s in backlog.stories),
                "",
            ])

        commit_msg_lines.extend([
            "Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>",
        ])

        commit_message = "\n".join(commit_msg_lines)

        logger.info("Committing changes: %s", message)
        try:
            self._run_git_command(["commit", "-m", commit_message])
        except RuntimeError as exc:
            # Provide helpful error message
            if "user.name" in str(exc) or "user.email" in str(exc) or "Author identity unknown" in str(exc):
                raise RuntimeError(
                    "Git user not configured. Please run:\n"
                    "  git config --global user.name 'Your Name'\n"
                    "  git config --global user.email 'your.email@example.com'"
                ) from exc
            raise

        # Get commit SHA
        result = self._run_git_command(["rev-parse", "HEAD"])
        commit_sha = result.stdout.strip()
        logger.info("Committed: %s", commit_sha[:8])

        return commit_sha

    def _ensure_git_user_configured(self) -> None:
        """Ensure git user.name and user.email are configured."""
        # Check user.name
        result = self._run_git_command(["config", "user.name"], check=False)
        has_name = bool(result.stdout.strip())

        # Check user.email
        result = self._run_git_command(["config", "user.email"], check=False)
        has_email = bool(result.stdout.strip())

        if not has_name or not has_email:
            # Try to set defaults from environment or use generic values
            if not has_name:
                default_name = os.environ.get("GIT_AUTHOR_NAME", "SDLC Agent")
                logger.info("Setting git user.name to: %s", default_name)
                self._run_git_command(["config", "user.name", default_name])

            if not has_email:
                default_email = os.environ.get("GIT_AUTHOR_EMAIL", "sdlc-agent@localhost")
                logger.info("Setting git user.email to: %s", default_email)
                self._run_git_command(["config", "user.email", default_email])

    def push_branch(self, branch_name: str | None = None, force: bool = False) -> None:
        """Push branch to remote origin.

        Args:
            branch_name: Branch name to push. If None, pushes current branch.
            force: Whether to force push
        """
        if branch_name is None:
            branch_name = self.get_current_branch()

        logger.info("Pushing branch %s to origin...", branch_name)

        args = ["push", "-u", "origin", branch_name]
        if force:
            args.append("--force")

        try:
            self._run_git_command(args, timeout=120)
            logger.info("Successfully pushed branch: %s", branch_name)
        except RuntimeError as exc:
            # Check if error is because branch already exists
            if "already exists" in str(exc) or "up-to-date" in str(exc):
                logger.info("Branch %s already up-to-date on remote", branch_name)
            else:
                raise

    def get_commit_sha(self) -> str:
        """Get the current commit SHA.

        Returns:
            Full commit SHA
        """
        result = self._run_git_command(["rev-parse", "HEAD"])
        return result.stdout.strip()

    def get_diff(self, base_branch: str = "main") -> str:
        """Get diff between current branch and base branch.

        Args:
            base_branch: Base branch to compare against

        Returns:
            Diff output
        """
        result = self._run_git_command(["diff", base_branch])
        return result.stdout

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes.

        Returns:
            True if there are uncommitted changes
        """
        result = self._run_git_command(["status", "--porcelain"])
        return bool(result.stdout.strip())

    def get_remote_url(self) -> str:
        """Get the URL of the origin remote.

        Returns:
            Remote URL
        """
        result = self._run_git_command(["remote", "get-url", "origin"])
        return result.stdout.strip()
