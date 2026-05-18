"""Mocked Confluence client — fetches a BRD page by URL/id."""
from __future__ import annotations

from pathlib import Path


class MockConfluenceClient:
    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self.fixtures_dir = fixtures_dir

    def fetch_page(self, ref: str) -> str:
        """Return raw page text.

        If `ref` looks like a local file path, read it. Otherwise return a
        canned BRD so demos work offline.
        """
        path = Path(ref)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return (
            "# Default BRD\n\n"
            "Customers want to view their account balance on the mobile app.\n"
        )
