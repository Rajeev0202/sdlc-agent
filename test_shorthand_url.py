"""Test shorthand URL extraction for Confluence integration.

This script validates that the Confluence client can extract page IDs
from various URL formats, including shorthand URLs.
"""
import sys
import io

# Fix Windows console encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from sdlc_agent.integrations.confluence_client import ConfluenceClient


def test_url_extraction():
    """Test page ID extraction from different URL formats."""
    client = ConfluenceClient()

    test_cases = [
        # (url, expected_page_id, description)
        (
            "https://company.atlassian.net/wiki/spaces/PROJ/pages/12345/Page+Title",
            "12345",
            "Standard Cloud URL with page ID in path"
        ),
        (
            "https://confluence.company.com/display/SPACE/Page?pageId=67890",
            "67890",
            "Display URL with pageId query parameter"
        ),
        (
            "https://company.atlassian.net/wiki/pages/viewpage.action?pageId=11111",
            "11111",
            "View page action URL"
        ),
        # Shorthand URL test would require a real redirect, so we test the pattern detection
    ]

    print("Testing Confluence URL Extraction")
    print("=" * 60)

    for url, expected_id, description in test_cases:
        try:
            page_id = client.extract_page_id(url)
            status = "✅ PASS" if page_id == expected_id else f"❌ FAIL (got {page_id})"
            print(f"{status} | {description}")
            print(f"         URL: {url}")
            print(f"         Expected: {expected_id}, Got: {page_id}")
        except Exception as e:
            print(f"❌ ERROR | {description}")
            print(f"          URL: {url}")
            print(f"          Error: {e}")
        print()

    # Test shorthand URL pattern detection
    print("Testing Shorthand URL Detection")
    print("=" * 60)
    shorthand_url = "https://company.atlassian.net/x/ABC123"
    try:
        # This will fail because it's not a real URL, but it proves the pattern is detected
        client.extract_page_id(shorthand_url)
        print(f"❌ UNEXPECTED | Shorthand URL should trigger resolution")
    except ValueError as e:
        if "_resolve_shorthand_url" in str(e) or "Failed to resolve" in str(e):
            print(f"✅ PASS | Shorthand URL pattern detected correctly")
            print(f"         Would attempt to resolve: {shorthand_url}")
        else:
            print(f"❌ FAIL | Unexpected error: {e}")
    print()


if __name__ == "__main__":
    test_url_extraction()

    print("\nNote:")
    print("- Shorthand URL resolution requires network access and valid credentials")
    print("- To test with real shorthand URLs, run:")
    print("  export CONFLUENCE_API_TOKEN='your-token'")
    print("  export CONFLUENCE_EMAIL='your-email@company.com'")
    print("  python -c \"from sdlc_agent.integrations import fetch_confluence_page; print(fetch_confluence_page('https://your-company.atlassian.net/x/ABC123'))\"")
