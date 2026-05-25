---
description: Show the current SDLC pipeline status — what stage you're on, what's been done, and what to run next. Invoke with /sdlc-status at any time.
allowed-tools: Read, mcp__jira__get_issue, mcp__github__get_pull_request
---

# SDLC Status

Read `.claude/sdlc-state.json` and present a clear pipeline status dashboard.

If the file doesn't exist, print:
```
ℹ️  No active SDLC session. Start with /sdlc-ingest <confluence-url-or-file>.
```

Otherwise, print a status board like:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SDLC Pipeline · <epic name>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅  Stage 1 · Ingest      <source>
  ✅  Stage 2 · Plan        <N> Jira cards created
  ✅  Stage 3 · Build       <branch> · <coverage>% coverage
  ✅  Stage 4 · Commit      <pr_url>
  🔄  Stage 5 · Review      In progress — <N> issues
  ⏳  Stage 6 · Fix         Not started
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ▶  Next: /sdlc-fix
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If a Jira card ID is in state, call `mcp__jira__get_issue` to get current card status.
If a PR number is in state, call `mcp__github__get_pull_request` to get live CI status.

Show live data where available.
