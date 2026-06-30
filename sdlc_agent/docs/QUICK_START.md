# Quick Start Guide - Fix Stage 1 Extraction

## Problem
Stage 1 shows "User Stories Extracted: 0" because the LLM extraction is failing in the web server context.

## Solution
Use Anthropic API instead of Claude Code CLI for reliable extraction.

## Steps

### 1. Get Anthropic API Key

1. Visit: https://console.anthropic.com/
2. Sign in or create account
3. Go to **API Keys** section  
4. Click **Create Key**
5. Copy the key (starts with `sk-ant-api03-...`)

### 2. Update .env File

Open `.env` file and update line 6:

**Before:**
```bash
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

**After:**
```bash
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_ACTUAL_KEY_HERE
```

💡 Replace `sk-ant-api03-YOUR_ACTUAL_KEY_HERE` with your real key from step 1.

### 3. Verify Configuration

Run the verification script:

```bash
python verify-api-key.py
```

**Expected output:**
```
[OK] API key found: sk-ant-api03-...
[OK] Client backend: anthropic (claude-3-5-sonnet-latest)
[SUCCESS] Anthropic API is configured and ready!
```

### 4. Start the Server

**Option A: Use the batch file (Windows)**
```bash
start-server.bat
```

**Option B: Manual start**
```bash
python -m sdlc_agent.web.app
```

Server will run on: **http://127.0.0.1:5002**

### 5. Test Stage 1

1. Open browser: http://127.0.0.1:5002
2. Go to **Stage 1: Requirements Ingestion**
3. Enter your Confluence URL
4. Click **Run Stage 1**

**Expected Result:**
```
✅ User Stories Extracted: 3
✅ Acceptance Criteria Found: 13
✅ Open Questions: 0
```

## Verification

After running Stage 1, check the latest run output:

```bash
# Find latest run
ls -lt runs/ | head -5

# Check the brief
cat runs/run-XXXXXXXXX/01_brief.json
```

You should see:
- `"functional_needs"` array populated
- `"stories"` array with user stories (if using skill automation)
- No "No user stories found" in `open_questions`

## Troubleshooting

### Still seeing "User Stories: 0"?

Check server logs:
```bash
tail -50 server.log | grep "ClaudeClient\|LLM extraction"
```

**Should see:**
```
[ClaudeClient] Using Anthropic API (claude-3-5-sonnet-latest)
[Ingest Parser] LLM extracted 3 stories, 10 ACs
```

**If you see "Claude Code CLI" instead:**
Add to `.env`:
```bash
SDLC_DISABLE_CLAUDE_CLI=true
```
Then restart the server.

### API Key Not Working?

1. Verify key starts with `sk-ant-api03-`
2. Check no extra spaces or quotes in `.env`
3. Make sure you have credit in your Anthropic account
4. Run `python verify-api-key.py` to diagnose

### Port Already In Use?

If port 5002 is busy:
1. Find the process: `netstat -ano | findstr :5002`
2. Kill it: `taskkill /PID <PID> /F`
3. Restart server

## What Changed

**Before (Claude Code CLI):**
- Subprocess calls from web server
- Timeouts and failures
- 0 stories extracted

**After (Anthropic API):**
- Direct API calls
- Reliable extraction
- Full token usage tracking
- 3+ stories extracted correctly

## Expected Extraction (Test Page)

For the test Confluence page about card freeze/unfreeze, you should get:

**Stories:** 3
1. Customer can freeze debit card
2. Customer can unfreeze after authentication  
3. Compliance officer can audit events

**Acceptance Criteria:** 10+
- Card freezes within 2 seconds
- Step-up auth required for unfreeze
- Events logged for 24 months
- etc.

**NFRs:** 4
- Performance requirements
- Security requirements
- Audit requirements
- Business impact metrics

## Files Created

- `start-server.bat` - Quick server startup script
- `verify-api-key.py` - Verify API configuration
- `QUICK_START.md` - This guide

## Next Steps

Once Stage 1 is working:
1. Run Stage 2 to create Jira cards
2. Run Stage 3 to generate code
3. Check token usage in `.claude/observability/metrics.json`

---

💡 **Tip:** The Anthropic API will also enable token usage tracking in `traces.jsonl` for cost analysis!
