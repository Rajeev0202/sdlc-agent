"""GitHub integration configuration.

Controls whether to use real GitHub REST API or mock client.
Requires GITHUB_TOKEN environment variable for real GitHub integration.
"""
import os
import logging

logger = logging.getLogger(__name__)


def should_use_real_github() -> bool:
    """Check if real GitHub integration should be used.

    Returns:
        True if GITHUB_TOKEN environment variable is set.
    """
    token = os.environ.get("GITHUB_TOKEN", "").strip()

    if token:
        logger.info("Real GitHub REST API integration enabled (GITHUB_TOKEN found)")
        return True

    logger.info("Using mock GitHub client (GITHUB_TOKEN not set)")
    return False


def should_post_review_comments() -> bool:
    """Check if review comments should be posted to GitHub.

    Returns:
        True if POST_REVIEW_COMMENTS env var is set to 'true' or '1',
        or defaults to True when GITHUB_TOKEN is available.
    """
    value = os.environ.get("POST_REVIEW_COMMENTS", "").lower()

    # Explicit setting
    if value in ("false", "0", "no"):
        return False
    if value in ("true", "1", "yes"):
        if not should_use_real_github():
            logger.warning(
                "POST_REVIEW_COMMENTS is set but GITHUB_TOKEN is not available. "
                "Review comments will not be posted."
            )
            return False
        return True

    # Default: post comments if GitHub is enabled
    return should_use_real_github()
