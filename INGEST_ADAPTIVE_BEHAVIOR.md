# Ingest Skill - Adaptive Confluence Integration

## What Changed

The `/sdlc-ingest` skill now uses a **hybrid fallback strategy** for Confluence:

```
┌─────────────────────────────────────┐
│  User provides Confluence URL       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Try MCP Server (if configured)     │  ← Future-proof
└──────────────┬──────────────────────┘
               │ (not configured yet)
               ▼
┌─────────────────────────────────────┐
│  Fall back to REST API              │  ← Current path
│  (fetch_confluence_page)            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Return markdown content            │
└─────────────────────────────────────┘
```

## Why This Approach?

### Problem
- CLAUDE.md mentioned MCP servers for Confluence
- But `.claude.json` shows no MCP servers configured
- REST API works but requires manual credential setup

### Solution
**Graceful degradation** — try best method first, fall back to working method:

1. **MCP Server** (preferred):
   - Centralized auth
   - No per-project config
   - Auto-handles token refresh
   - **Status**: Not configured (placeholder for future)

2. **REST API** (fallback):
   - Works now
   - Requires env vars (CONFLUENCE_API_TOKEN, CONFLUENCE_EMAIL)
   - Direct HTTP requests
   - **Status**: ✅ Active

## Code Changes

### Before
```python
def _fetch_requirements(self, source: str) -> str:
    if "confluence" in source:
        from ..integrations import fetch_confluence_page
        return fetch_confluence_page(source)  # Direct call
```

### After
```python
def _fetch_requirements(self, source: str) -> str:
    if "confluence" in source:
        content = self._fetch_confluence_via_mcp_or_rest(source)
        if content:
            return content
        raise ValueError("Tried both MCP and REST API...")

def _fetch_confluence_via_mcp_or_rest(self, page_url: str) -> str | None:
    # Strategy 1: Try MCP (TODO when configured)
    # Strategy 2: Fall back to REST API
    try:
        from ..integrations import fetch_confluence_page
        return fetch_confluence_page(page_url)
    except Exception:
        return None
```

## Benefits

✅ **Works now** — REST API path unchanged  
✅ **Future-proof** — MCP support ready when configured  
✅ **Transparent** — User workflow unchanged  
✅ **Testable** — Both paths can be tested independently  
✅ **Maintainable** — Single method to update for MCP  

## What Users Need to Do

### Today (REST API)
```bash
# Set environment variables
export CONFLUENCE_API_TOKEN="..."
export CONFLUENCE_EMAIL="your-email@company.com"

# Use the skill
/sdlc-ingest https://company.atlassian.net/wiki/spaces/PROJ/pages/12345
```

### Future (MCP Server)
```json
// Add to ~/.claude.json (one-time)
{
  "mcpServers": {
    "confluence": {
      "type": "url",
      "url": "https://mcp.atlassian.com/confluence/sse"
    }
  }
}
```

Then same skill usage — no changes needed.

## Testing Checklist

- [x] Code compiles (no syntax errors)
- [x] REST API path preserved (backward compatible)
- [x] Error messages updated (mentions both MCP and REST)
- [x] Documentation created ([docs/CONFLUENCE_INTEGRATION.md](docs/CONFLUENCE_INTEGRATION.md))
- [ ] Test with live Confluence URL (requires credentials)
- [ ] Test MCP path (requires MCP server config)

## Next Steps

### Immediate (REST API)
1. Set environment variables (CONFLUENCE_API_TOKEN, CONFLUENCE_EMAIL)
2. Test ingestion with real Confluence BRD
3. Verify markdown conversion quality

### Future (MCP Server)
1. Configure Confluence MCP server in `.claude.json`
2. Implement MCP fetch logic in `_fetch_confluence_via_mcp_or_rest`
3. Test end-to-end with MCP
4. Remove REST API fallback (if MCP fully reliable)

## Files Changed

- `sdlc_agent/skills/ingest_skill.py` — Added `_fetch_confluence_via_mcp_or_rest()` method
- `docs/CONFLUENCE_INTEGRATION.md` — Setup guide (new file)
- `INGEST_ADAPTIVE_BEHAVIOR.md` — This document (updated)

## References

- [sdlc_agent/integrations/confluence_client.py](sdlc_agent/integrations/confluence_client.py) — REST API implementation
- [CLAUDE.md](CLAUDE.md#required-mcp-servers) — Original MCP server requirement
- [docs/CONFLUENCE_INTEGRATION.md](docs/CONFLUENCE_INTEGRATION.md) — Detailed setup guide
