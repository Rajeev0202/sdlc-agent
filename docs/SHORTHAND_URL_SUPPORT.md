# Shorthand URL Support in Confluence Integration

## Question
**Does the MCP server support shorthand URL extraction?**

## Answer

### Current Implementation (REST API)
✅ **Yes, shorthand URLs are now supported** via the REST API fallback.

The REST API client now automatically resolves shorthand URLs like:
```
https://company.atlassian.net/x/ABC123
```

**How it works:**
1. Detect `/x/` pattern in URL
2. Follow HTTP redirect to get full URL
3. Extract page ID from final URL
4. Fetch page content normally

**Code:** [confluence_client.py:82-123](../sdlc_agent/integrations/confluence_client.py#L82-L123)

### Future Implementation (MCP Server)
⚠️ **Unknown** — MCP server not yet configured.

When MCP server is configured, it will depend on the MCP provider's implementation:

- **If MCP handles URL resolution**: Pass shorthand URL as-is, MCP resolves internally
- **If MCP requires page IDs**: We'll need to resolve shorthand URLs before calling MCP

**Implementation strategy:**
```python
def _fetch_confluence_via_mcp_or_rest(self, page_url: str) -> str | None:
    # Option 1: Try MCP with original URL
    try:
        content = mcp_fetch_page(page_url)  # MCP might handle shorthand
        if content:
            return content
    except Exception:
        pass
    
    # Option 2: Resolve URL first, then try MCP
    # (Needed if MCP requires page IDs only)
    try:
        full_url = self._resolve_if_shorthand(page_url)
        content = mcp_fetch_page(full_url)
        if content:
            return content
    except Exception:
        pass
    
    # Option 3: Fall back to REST API (current implementation)
    return fetch_confluence_page(page_url)  # Handles shorthand internally
```

## Examples

### Shorthand URL
```bash
/sdlc-ingest https://natwest.atlassian.net/x/XYZ789
```

**What happens:**
1. REST API client detects `/x/` pattern
2. Sends `HEAD` request to follow redirect
3. Gets redirected to: `https://natwest.atlassian.net/wiki/spaces/PROJ/pages/12345/BRD+Title`
4. Extracts page ID: `12345`
5. Fetches content via REST API: `GET /wiki/api/v2/pages/12345`
6. Converts HTML to markdown
7. Returns content to ingestion parser

### Full URL (Traditional)
```bash
/sdlc-ingest https://natwest.atlassian.net/wiki/spaces/PROJ/pages/12345/BRD+Title
```

**What happens:**
1. REST API client extracts page ID directly: `12345`
2. Fetches content (same as step 5 above)
3. Returns markdown

## Testing

### Manual Test (REST API)
```python
from sdlc_agent.integrations import ConfluenceClient

client = ConfluenceClient()

# Test shorthand URL
shorthand = "https://your-company.atlassian.net/x/ABC123"
page_id = client.extract_page_id(shorthand)
print(f"Resolved page ID: {page_id}")

# Test full fetch
content = client.get_page_content(shorthand)
print(f"Title: {content['title']}")
print(f"Content length: {len(content['content'])} chars")
```

### Expected Output
```
DEBUG: Resolved shorthand URL: https://company.atlassian.net/x/ABC123 -> https://company.atlassian.net/wiki/spaces/PROJ/pages/12345/Title
Resolved page ID: 12345
Title: BRD - Card Freeze Feature
Content length: 5432 chars
```

## Limitations

### REST API Method
- ⚠️ Requires network access to resolve redirect
- ⚠️ Adds ~100-200ms latency (one extra HTTP request)
- ⚠️ Fails if shorthand URL is private/restricted
- ⚠️ Requires authentication for private pages

### MCP Server Method (Future)
- ✅ May handle resolution server-side (faster)
- ✅ May leverage existing OAuth session
- ❓ Unknown if it supports shorthand URLs natively

## Recommendations

### For Users
1. **Prefer full URLs** when possible (faster, more reliable)
2. **Shorthand URLs work** but add slight latency
3. **If shorthand fails**, open page in browser and copy full URL

### For Developers
1. **Keep REST API fallback** even when MCP is configured (handles edge cases)
2. **Test MCP with shorthand URLs** once configured
3. **Document MCP behavior** in this file after testing

## Related Files

- [confluence_client.py](../sdlc_agent/integrations/confluence_client.py) — REST API implementation with shorthand support
- [ingest_skill.py](../sdlc_agent/skills/ingest_skill.py) — Uses `_fetch_confluence_via_mcp_or_rest()`
- [CONFLUENCE_INTEGRATION.md](CONFLUENCE_INTEGRATION.md) — General setup guide

## Status

| Feature | REST API | MCP Server |
|---------|----------|------------|
| Full URL (`/pages/12345`) | ✅ Supported | ⚠️ Unknown (not configured) |
| Query param (`?pageId=12345`) | ✅ Supported | ⚠️ Unknown |
| Shorthand (`/x/ABC123`) | ✅ **NEW - Supported** | ⚠️ Unknown |
| HTML → Markdown | ✅ Supported | ⚠️ Unknown |
| Auth (API token) | ✅ Supported | ⚠️ Unknown |
| Auth (OAuth) | ❌ Not supported | ⚠️ Unknown |

---

**Last Updated:** 2026-06-21  
**Author:** SDLC Agent Team  
**Next Review:** After MCP server is configured
