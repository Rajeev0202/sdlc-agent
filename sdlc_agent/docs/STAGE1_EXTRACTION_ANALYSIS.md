# Stage 1 User Story Extraction — Analysis & Fix

## Issue Summary

Stage 1 reports:
```
User Stories Extracted: 0
Acceptance Criteria Found: 0
Open Questions: 3
```

## Root Cause

The LLM extraction is working perfectly in isolation, but the web app is not receiving/processing the LLM results correctly. 

### Evidence

**Test 1: Direct LLM Call (WORKS ✓)**
```bash
$ python test_llm_extraction.py
Backend: claude-code-cli

Result:
{
  "epic": "Mobile App Account Balance View",
  "stories": [
    {
      "as_a": "Customer",
      "i_want": "view my account balance on the mobile app",
      "so_that": "I can check my current funds",
      "acceptance_criteria": [
        "Balance displayed on mobile app",
        "Balance loads within 2 seconds",
        ...
      ]
    }
  ]
}

[OK] Extracted 1 stories
```

**Test 2: Web App Execution (FAILS ✗)**
```
server.log:
[Ingest Parser] Attempting LLM extraction via claude-code-cli
[Ingest Parser] LLM extraction returned no stories, falling back to regex
[Ingest Parser] Found 0 user stories
```

## Analysis

Looking at the code flow in `sdlc_agent/skills/ingest_skill.py`:

```python
# Line 117-124
if self.llm.is_live and len(cleaned.strip()) > 50:
    print(f"[Ingest Parser] Attempting LLM extraction via {self.llm.backend}")
    llm_result = self._llm_extract(cleaned)
    if llm_result and llm_result.get("stories"):   # ← CHECK HERE
        print(f"[Ingest Parser] LLM extracted {len(llm_result['stories'])} stories")
        return llm_result
    print(f"[Ingest Parser] LLM extraction returned no stories, falling back to regex")
```

The check `if llm_result and llm_result.get("stories")` requires stories to be non-empty. But the LLM _is_ returning stories!

## Hypothesis

1. **Timing issue** — The Claude Code CLI might be timing out in the web context
2. **JSON parsing issue** — The response might be getting mangled in the web flow
3. **Silent exception** — An exception is being caught and logged but not surfaced

## Debug Steps Added

Added enhanced logging in `ingest_skill.py` line 284-295:

```python
if not result:
    print("[Ingest Parser] LLM returned None/empty result")
    return None

if not isinstance(result, dict):
    print(f"[Ingest Parser] LLM returned non-dict: {type(result)}")
    return None

# Debug: show what the LLM returned
stories_count = len(result.get("stories", []))
ac_count = len(result.get("acceptance_criteria", []))
print(f"[Ingest Parser] LLM raw result: {stories_count} stories, {ac_count} ACs")
if stories_count == 0:
    print(f"[Ingest Parser] LLM full result: {json.dumps(result)[:500]}")
```

## Next Steps

### Option 1: Run with Enhanced Logging

1. Restart the web server
2. Try Stage 1 ingestion again
3. Check `server.log` for the new debug output:
   ```bash
   grep "LLM raw result\|LLM returned\|LLM full result" server.log
   ```

### Option 2: Direct API Key (Bypass CLI)

If Claude Code CLI is unreliable in the web context, switch to direct Anthropic API:

```bash
# In .env
ANTHROPIC_API_KEY=your_key_here
```

Then the `ClaudeClient` will use the Messages API instead of the CLI subprocess.

### Option 3: Use Gemini (Free Alternative)

```bash
# In .env
GOOGLE_API_KEY=your_key_here
pip install google-genai
```

### Option 4: Fallback Enhancement

Even if LLM extraction fails, we can improve the regex fallback to handle prose descriptions:

```python
# Add to ingest_skill.py around line 160
# If no formal stories found, create one from the epic/title
if not result["stories"] and result["epic"]:
    # Infer a basic story from the title/content
    result["stories"].append({
        "as_a": "User",
        "i_want": result["epic"].lower(),
        "so_that": "I can achieve the business objective",
        "acceptance_criteria": result.get("acceptance_criteria", [])
    })
```

## Quick Fix (Immediate)

The immediate fix is to check `_llm_extract` return value more carefully:

```python
# In ingest_skill.py line 119
llm_result = self._llm_extract(cleaned)
if llm_result:  # Changed from: if llm_result and llm_result.get("stories")
    stories = llm_result.get("stories", [])
    if stories:
        print(f"[Ingest Parser] LLM extracted {len(stories)} stories")
        return llm_result
    else:
        # LLM returned valid JSON but no stories - still use NFRs/dependencies
        print(f"[Ingest Parser] LLM returned valid structure but no stories")
        print(f"[Ingest Parser] Using {len(llm_result.get('nfr', []))} NFRs, {len(llm_result.get('dependencies', []))} deps")
        # Fall through to regex for stories, but keep LLM-extracted NFRs/deps
        result = llm_result  # Will be merged with regex results
```

## Testing

After applying the fix, test with:

```bash
# Minimal content (prose description)
curl -X POST http://localhost:5001/api/stage-1 \
  -H "Content-Type: application/json" \
  -d '{"source": "https://rrjha82.atlassian.net/.../Test-page"}'

# Expected output:
# stories_found: 1
# acceptance_criteria_found: 4
```

## Status

- ✓ LLM extraction confirmed working in isolation
- ✓ Enhanced debug logging added
- ⏳ Waiting to see new logs with debug output
- ⏳ Quick fix ready to apply once root cause is confirmed
