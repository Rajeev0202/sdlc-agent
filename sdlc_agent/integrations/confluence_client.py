"""Confluence integration — real REST client and an offline mock.

Mirrors the layout of ``jira_client.py`` (real + mock in one module):

* :class:`ConfluenceClient` / :func:`fetch_confluence_page` — live Confluence
  Cloud or Server/Data Center access via the REST API.
* :class:`MockConfluenceClient` — reads a local file or returns a canned BRD so
  demos run offline without credentials.
"""
from __future__ import annotations

import html as html_lib
import logging
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class ConfluenceClient:
    """Simple Confluence REST API client (Cloud and Server/Data Center)."""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        """Initialize the client.

        Args:
            base_url: Confluence base URL (e.g. https://company.atlassian.net).
                If omitted, it is read from ``CONFLUENCE_BASE_URL`` or derived
                from the page URL.
            token: API token; falls back to ``CONFLUENCE_API_TOKEN`` /
                ``ATLASSIAN_TOKEN``.
        """
        self.base_url = base_url or os.getenv("CONFLUENCE_BASE_URL")
        self.token = token or os.getenv("CONFLUENCE_API_TOKEN") or os.getenv("ATLASSIAN_TOKEN")
        self.email = os.getenv("CONFLUENCE_EMAIL") or os.getenv("ATLASSIAN_EMAIL")

        logger.debug(
            "ConfluenceClient initialized (email=%s, token=%s, base_url=%s)",
            "set" if self.email else "missing",
            "set" if self.token else "missing",
            self.base_url or "from-page-url",
        )

    def extract_page_id(self, url: str) -> str:
        """Extract the numeric page ID from a Confluence URL.

        Supports formats:
        - https://company.atlassian.net/wiki/spaces/SPACE/pages/12345/Page+Title
        - https://confluence.company.com/display/SPACE/Page+Title?pageId=12345
        - https://company.atlassian.net/wiki/pages/viewpage.action?pageId=12345
        """
        if "pageId=" in url:
            match = re.search(r"pageId=(\d+)", url)
            if match:
                return match.group(1)

        match = re.search(r"/pages/(\d+)", url)
        if match:
            return match.group(1)

        raise ValueError(f"Could not extract page ID from URL: {url}")

    def get_page_content(self, page_url: str) -> dict:
        """Fetch page content from Confluence.

        Args:
            page_url: Full Confluence page URL.

        Returns:
            dict with ``id``, ``title``, ``content``, ``space``, ``url``.
        """
        # Extract base URL if not provided
        if not self.base_url:
            parsed = urlparse(page_url)
            self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        page_id = self.extract_page_id(page_url)

        # Confluence Cloud uses /wiki/api/v2, Server/DC uses /rest/api
        if "atlassian.net" in self.base_url:
            api_url = f"{self.base_url}/wiki/api/v2/pages/{page_id}"
            params = {"body-format": "storage"}
        else:
            api_url = f"{self.base_url}/rest/api/content/{page_id}"
            params = {"expand": "body.storage,space"}

        headers = {"Accept": "application/json"}

        if self.token and self.email:
            # Confluence Cloud (email + token)
            auth = (self.email, self.token)
        elif self.token:
            # Server/DC with PAT or API token
            headers["Authorization"] = f"Bearer {self.token}"
            auth = None
        else:
            raise ValueError(
                "Confluence credentials not found. Please set:\n"
                "- CONFLUENCE_API_TOKEN (and CONFLUENCE_EMAIL for Cloud)\n"
                "- Or ATLASSIAN_TOKEN (and ATLASSIAN_EMAIL)\n"
                "in your .env file or environment variables."
            )

        logger.debug(
            "Confluence API request: url=%s params=%s auth=%s",
            api_url, params, "email+token" if auth else "bearer",
        )

        response = requests.get(api_url, headers=headers, auth=auth, params=params)

        if response.status_code != 200:
            logger.error(
                "Confluence API returned %s: %s", response.status_code, response.text[:500]
            )
            if response.status_code == 404:
                raise ValueError(
                    f"Confluence page not found (404).\n"
                    f"URL: {api_url}\n"
                    f"Page ID: {page_id}\n\n"
                    f"Possible reasons:\n"
                    f"1. Page doesn't exist or was deleted\n"
                    f"2. You don't have permission to view this page\n"
                    f"3. Page ID extraction failed\n\n"
                    f"Please verify the page URL in your browser and check permissions."
                )
            response.raise_for_status()

        data = response.json()

        # Parse response (format differs between Cloud and Server)
        if "atlassian.net" in self.base_url:
            return {
                "id": data["id"],
                "title": data["title"],
                "content": data.get("body", {}).get("storage", {}).get("value", ""),
                "space": data.get("spaceId", ""),
                "url": page_url,
            }
        return {
            "id": data["id"],
            "title": data["title"],
            "content": data.get("body", {}).get("storage", {}).get("value", ""),
            "space": data.get("space", {}).get("key", ""),
            "url": page_url,
        }

    def html_to_markdown(self, html: str) -> str:
        """Convert Confluence HTML storage format to basic markdown.

        This is a simple converter — for production use, consider a library like
        html2text or markdownify.
        """
        # Decode HTML entities
        text = html_lib.unescape(html)

        # Confluence macros: EXTRACT content from code blocks (don't strip them).
        # Users often paste requirements inside code/markdown blocks. The actual
        # content is in <ac:plain-text-body><![CDATA[...]]></ac:plain-text-body>.
        def _extract_macro_content(match):
            macro_html = match.group(0)
            cdata_match = re.search(
                r"<ac:plain-text-body>\s*<!\[CDATA\[(.*?)\]\]>\s*</ac:plain-text-body>",
                macro_html,
                flags=re.DOTALL,
            )
            if cdata_match:
                return "\n" + cdata_match.group(1) + "\n"
            rich_match = re.search(
                r"<ac:rich-text-body>(.*?)</ac:rich-text-body>",
                macro_html,
                flags=re.DOTALL,
            )
            if rich_match:
                return "\n" + rich_match.group(1) + "\n"
            return ""

        text = re.sub(
            r"<ac:structured-macro[^>]*>.*?</ac:structured-macro>",
            _extract_macro_content,
            text,
            flags=re.DOTALL,
        )

        # Clean up remaining Confluence-specific tags
        text = re.sub(r"<ac:[^>]*?/>", "", text)
        text = re.sub(r"<ri:[^>]*?/>", "", text)
        text = re.sub(r"<ac:[^>]*>", "", text)
        text = re.sub(r"</ac:[^>]*>", "", text)

        # Headings
        for level in range(1, 7):
            text = re.sub(
                rf"<h{level}[^>]*>(.*?)</h{level}>",
                lambda m, lv=level: f"\n{'#' * lv} {m.group(1)}\n",
                text,
                flags=re.DOTALL,
            )

        # Bold / italic
        text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
        text = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)
        text = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)
        text = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", text, flags=re.DOTALL)

        # Lists
        text = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", text, flags=re.DOTALL)
        text = re.sub(r"<ul[^>]*>", "\n", text)
        text = re.sub(r"</ul>", "\n", text)
        text = re.sub(r"<ol[^>]*>", "\n", text)
        text = re.sub(r"</ol>", "\n", text)

        # Paragraphs and breaks
        text = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", text, flags=re.DOTALL)
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<div[^>]*>", "\n", text)
        text = re.sub(r"</div>", "\n", text)

        # Tables
        text = re.sub(r"<td[^>]*>(.*?)</td>", r" | \1", text, flags=re.DOTALL)
        text = re.sub(r"<th[^>]*>(.*?)</th>", r" | \1", text, flags=re.DOTALL)
        text = re.sub(r"<tr[^>]*>", "\n", text)
        text = re.sub(r"</tr>", "\n", text)

        # Remove remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" +\n", "\n", text)

        return text.strip()


def fetch_confluence_page(page_url: str) -> str:
    """Fetch a Confluence page and return its content as markdown text."""
    client = ConfluenceClient()
    page_data = client.get_page_content(page_url)
    markdown = client.html_to_markdown(page_data["content"])
    if not markdown.startswith("#"):
        markdown = f"# {page_data['title']}\n\n{markdown}"
    return markdown


class MockConfluenceClient:
    """Offline Confluence client — reads a local file or returns a canned BRD."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self.fixtures_dir = fixtures_dir

    def fetch_page(self, ref: str) -> str:
        """Return raw page text.

        If ``ref`` looks like a local file path, read it. Otherwise return a
        canned BRD so demos work offline.
        """
        path = Path(ref)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return (
            "# Default BRD\n\n"
            "Customers want to view their account balance on the mobile app.\n"
        )
