# Confluence Integration Guide

## Overview

The SDLC Agent supports fetching requirements from Confluence pages through two methods:

1. **MCP Server** (preferred, when configured)
2. **REST API** (fallback, requires credentials)

## Current Status

**MCP Server**: ❌ Not configured  
**REST API**: ✅ Available (requires setup)

## Setup Instructions

### Option 1: MCP Server (Recommended)

MCP (Model Context Protocol) provides authenticated access to Confluence without managing API tokens directly.

#### Configuration

Add to your `~/.claude.json` or project `.claude/settings.json`:

```json
{
  "mcpServers": {
    "confluence": {
      "type": "url",
      "url": "https://mcp.atlassian.com/confluence/sse",
      "note": "Requires Atlassian API token in env: ATLASSIAN_TOKEN"
    }
  }
}
```

#### Environment Variables

```bash
# For Confluence Cloud
export ATLASSIAN_TOKEN="your-api-token-here"
export ATLASSIAN_EMAIL="your-email@company.com"
```

#### Benefits

- ✅ Centralized authentication
- ✅ Auto-handles OAuth/token refresh
- ✅ Works across all Claude Code sessions
- ✅ No code changes needed

### Option 2: REST API (Current Fallback)

Direct REST API access requires explicit credentials.

#### Environment Variables

Create a `.env` file in the project root:

```bash
# For Confluence Cloud
CONFLUENCE_API_TOKEN="your-api-token-here"
CONFLUENCE_EMAIL="your-email@company.com"
CONFLUENCE_BASE_URL="https://your-company.atlassian.net"

# Alternative: Use Atlassian variables (works for both Jira and Confluence)
ATLASSIAN_TOKEN="your-api-token-here"
ATLASSIAN_EMAIL="your-email@company.com"
```

#### Obtaining API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it (e.g., "SDLC Agent")
4. Copy the token and add to `.env`

#### For Confluence Server/Data Center

```bash
CONFLUENCE_BASE_URL="https://confluence.your-company.com"
CONFLUENCE_API_TOKEN="your-personal-access-token"
# Email not required for Server/DC
```

## How It Works

The ingestion logic uses a **fallback strategy**:

```python
def _fetch_confluence_via_mcp_or_rest(page_url):
    # 1. Try MCP server (if configured)
    #    - Checks for available MCP tools
    #    - Uses authenticated session
    
    # 2. Fall back to REST API
    #    - Uses environment credentials
    #    - Direct HTTP requests
    
    # 3. Return None if both fail
    #    - Caller raises helpful error
```

## Usage

Once configured, simply pass a Confluence URL to `/sdlc-ingest`:

```bash
/sdlc-ingest https://your-company.atlassian.net/wiki/spaces/PROJ/pages/12345/BRD+Card+Freeze
```

The system will automatically:
1. Try MCP (if configured)
2. Fall back to REST API (if credentials set)
3. Convert HTML storage format to markdown
4. Extract structured requirements

## Troubleshooting

### "Failed to fetch Confluence page"

**Check:**
1. Is the page URL correct? Copy it from your browser.
2. Do you have permission to view the page?
3. Are credentials set correctly?

```bash
# Verify environment variables
env | grep -i "CONFLUENCE\|ATLASSIAN"
```

### "404 Page Not Found"

**Possible reasons:**
- Page was deleted or moved
- You don't have view permissions
- Page ID extraction failed (try a different URL format)

**Try:**
- Open the page in a browser while logged in
- Check the URL format (see supported formats below)

### Supported URL Formats

```
✅ https://company.atlassian.net/wiki/spaces/SPACE/pages/12345/Page+Title
✅ https://confluence.company.com/display/SPACE/Page+Title?pageId=12345
✅ https://company.atlassian.net/wiki/pages/viewpage.action?pageId=12345
✅ https://company.atlassian.net/x/ABC123 (shorthand/tiny URL - auto-resolved)
```

**Note on Shorthand URLs:**
- Shorthand URLs (`/x/ABC123`) are automatically resolved by following the redirect
- This requires network access to your Confluence instance
- If resolution fails, open the page in your browser and copy the full URL

### SSL Certificate Issues (Windows)

If you see SSL verification errors:

```bash
# Install certifi for Windows
python -m pip install certifi python-certifi-win32
```

## Testing

Test your Confluence connection:

```python
from sdlc_agent.integrations import fetch_confluence_page

# Replace with your page URL
url = "https://your-company.atlassian.net/wiki/spaces/PROJ/pages/12345"
content = fetch_confluence_page(url)
print(f"Fetched {len(content)} characters")
```

## Migration Path

### Current State
- ✅ REST API working
- ❌ MCP not configured

### Future Enhancement
When MCP server is added:

1. Add MCP server to `.claude.json` (one-time setup)
2. Code automatically prefers MCP over REST API
3. No changes to user workflow
4. Fallback remains for offline/testing scenarios

## Security Notes

⚠️ **Never commit credentials**
- `.env` is in `.gitignore`
- Use environment variables, not hardcoded tokens
- Rotate tokens if accidentally exposed

✅ **TLS verification**
- Always enabled (`verify=True`)
- Uses `certifi` CA bundle on Windows
- Rejects `verify=False` per NatWest standards

## References

- [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
- [Confluence REST API Docs](https://developer.atlassian.com/cloud/confluence/rest/v2/)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
