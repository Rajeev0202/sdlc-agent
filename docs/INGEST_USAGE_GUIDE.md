# SDLC Ingest Skill - Usage Guide

## Quick Start

### 1. From Confluence (Shareable Link)

```bash
/sdlc-ingest https://your-company.atlassian.net/wiki/spaces/PROJ/pages/123456/Card+Freeze+BRD
```

**Prerequisites**:
- Set `CONFLUENCE_API_TOKEN` (or `ATLASSIAN_TOKEN`) in `.env`
- Set `CONFLUENCE_EMAIL` (or `ATLASSIAN_EMAIL`) for Confluence Cloud
- For Server/DC: just `CONFLUENCE_API_TOKEN` (Personal Access Token)

**What happens**:
1. Fetches the page via Confluence REST API
2. Converts HTML to markdown
3. **Smart parsing**:
   - If BRD has formal "As a X, I want Y, so that Z" → Extract as-is (fast)
   - If BRD has bullets/prose → LLM converts to user stories
4. Saves structured requirements to `.claude/sdlc-state.json`

---

### 2. From Local File

```bash
/sdlc-ingest requirements/card_freeze.md
/sdlc-ingest requirements/card_freeze.txt
```

Supports: `.md`, `.txt` (`.docx` and `.pdf` coming soon)

---

## How It Adapts to Your BRD Format

### Format 1: Formal User Stories (No LLM Needed)

If your BRD already has this format:

```markdown
# Card Freeze Feature

## User Stories

As a Customer, I want to freeze my debit card instantly via mobile app,
so that I can prevent fraudulent transactions immediately.

As a Customer, I want to unfreeze my previously frozen card,
so that I can resume normal card usage.

## Acceptance Criteria
- Card status updates to FROZEN within 2 seconds
- Push notification sent on successful freeze
```

**Result**: Stories extracted via regex (instant, no API calls)

---

### Format 2: Informal Requirements (LLM Conversion)

If your BRD has bullet points or prose:

```markdown
# Card Freeze Feature

## Requirements

The mobile app should allow customers to:
- Freeze their debit card instantly
- Unfreeze their card when needed
- View freeze/unfreeze history

Support agents need the ability to:
- View customer's card freeze history for troubleshooting
```

**Result**: LLM converts bullets into 4 atomic user stories with personas inferred

---

### Format 3: Mixed (Confluence Code Blocks, Tables)

Confluence often wraps requirements in macros:

```html
<ac:structured-macro ac:name="code">
    <ac:plain-text-body><![CDATA[
As a Customer, I want to freeze my card, so that I can prevent fraud.

Acceptance Criteria:
- Freeze within 2 seconds
    ]]></ac:plain-text-body>
</ac:structured-macro>
```

**Result**: Macro content extracted, then parsed normally

---

## What Gets Extracted

The skill extracts these sections from any BRD format:

| Section | How It's Found |
|---------|----------------|
| **Epic/Title** | First heading (`# Title`) |
| **User Stories** | Regex (formal) OR LLM (informal) |
| **Acceptance Criteria** | Bullets under "Acceptance Criteria" or "Definition of Done" |
| **NFRs** | Lines with keywords: performance, security, scalability, availability |
| **Out of Scope** | Bullets under "Out of Scope" or "Not in Scope" |
| **Dependencies** | Lines with: "depends on", "requires", "integration with" |

---

## Output Format

The skill saves to `.claude/sdlc-state.json`:

```json
{
  "stage": "ingest",
  "source": "https://confluence.example.com/123",
  "epic": "Card Freeze Feature",
  "stories": [
    {
      "as_a": "Customer",
      "i_want": "freeze my debit card instantly via mobile app",
      "so_that": "I can prevent fraudulent transactions immediately",
      "acceptance_criteria": [
        "Card status updates to FROZEN within 2 seconds"
      ]
    },
    {
      "as_a": "Customer",
      "i_want": "unfreeze my previously frozen card",
      "so_that": "I can resume normal card usage"
    }
  ],
  "acceptance_criteria": [
    "All operations must be audited",
    "System must handle 1000 concurrent users"
  ],
  "nfr": [
    "Performance: API response time < 500ms at p95",
    "Security: All endpoints require OAuth2"
  ],
  "out_of_scope": [
    "Credit card freeze",
    "Physical card replacement"
  ],
  "dependencies": [
    "Card Management Service v2.1"
  ],
  "open_questions": [],
  "timestamp": "2026-06-19T10:30:00Z"
}
```

---

## Configuration

### Required for Confluence

Create `.env` in project root:

```bash
# For Confluence Cloud (atlassian.net)
CONFLUENCE_API_TOKEN=your-api-token
CONFLUENCE_EMAIL=your-email@company.com

# OR use Atlassian unified tokens
ATLASSIAN_TOKEN=your-api-token
ATLASSIAN_EMAIL=your-email@company.com

# For Confluence Server/Data Center
CONFLUENCE_API_TOKEN=your-personal-access-token
CONFLUENCE_BASE_URL=https://confluence.yourcompany.com
```

**How to get tokens**:
- Confluence Cloud: [API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
- Server/DC: Admin → Personal Access Tokens

---

### Required for LLM Conversion (Informal BRDs)

```bash
# Option 1: Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# Option 2: Auto-detected from Claude Code CLI (no config needed)
```

If neither is available, the skill falls back to regex-only extraction.

---

## Troubleshooting

### "Confluence page not found (404)"

**Causes**:
1. Page doesn't exist or was deleted
2. No permission to view the page
3. Wrong URL format

**Fix**:
- Open the page in your browser first to verify it exists
- Check you have view permissions
- Use the shareable link format: `https://your-company.atlassian.net/wiki/spaces/SPACE/pages/12345/Page+Title`

---

### "No user stories found"

**Causes**:
1. BRD has no formal "As a X, I want Y" stories
2. LLM not available (no API key)
3. Content is too short (< 50 chars)

**Fix**:
- Check if `ANTHROPIC_API_KEY` is set
- Verify BRD has actual requirements (not just a title)
- Look at console logs: `[Ingest Parser] Regex found 0 formal user stories`

---

### "SSL certificate verify failed" (Windows)

**Fix**:
```bash
pip install certifi python-certifi-win32
```

This installs proper SSL certificates for Windows.

---

## Next Steps After Ingestion

After `/sdlc-ingest` completes:

1. **Review the output**: Check `.claude/sdlc-state.json`
2. **Answer open questions**: The skill may flag ambiguities
3. **Run Stage 2**: `/sdlc-plan PROJECT-KEY` to create Jira cards

---

## Examples

### Example 1: Ingest from Confluence

```bash
/sdlc-ingest https://natwest.atlassian.net/wiki/spaces/BANKING/pages/789/Card+Freeze+BRD
```

**Output**:
```
✓ Fetched Confluence page "Card Freeze BRD"
✓ Extracted 3 user stories (formal format)
✓ Found 5 acceptance criteria
✓ Found 2 NFRs
✓ Saved to .claude/sdlc-state.json

Open questions:
Q1. [Acceptance Criteria] — "Card freezes quickly" is too vague. What is the specific time requirement?
Q2. [NFR] — Are there any security requirements?
```

---

### Example 2: Ingest from Local File

```bash
/sdlc-ingest samples/brd_card_freeze.md
```

**Output**:
```
✓ Read local file: samples/brd_card_freeze.md
✓ No formal stories found - using LLM to convert requirements
✓ LLM extracted 4 user stories from bullet points
✓ Saved to .claude/sdlc-state.json
```

---

## Advanced: Programmatic Usage

For UI integration or automation:

```python
from pathlib import Path
from sdlc_agent.skills.ingest_skill import IngestSkillAutomation

# Initialize
skill = IngestSkillAutomation(Path("."))

# Run ingestion
state = skill.run("https://confluence.example.com/wiki/pages/123")

# Access results
print(f"Epic: {state['epic']}")
print(f"Stories: {len(state['stories'])}")
for story in state['stories']:
    print(f"  - {story['as_a']}: {story['i_want']}")
```

---

## Testing

Run the test suite to verify the skill works:

```bash
# Test formal vs informal BRDs
python test_ingest_adaptive.py

# Test Confluence HTML conversion
python test_confluence_to_stories.py
```

---

## See Also

- [Adaptive Behavior Details](../INGEST_ADAPTIVE_BEHAVIOR.md)
- [Confluence Setup Guide](CONFLUENCE_SETUP.md)
- [Full SDLC Pipeline](../CLAUDE.md)
