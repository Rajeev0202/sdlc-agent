---
description: SDLC Stage 1 — Ingest requirements from Confluence pages or uploaded Word/PDF docs, extract structured acceptance criteria, surface ambiguities, and save to sdlc-state.json. Invoke with /sdlc-ingest <confluence-page-url-or-filename>.
allowed-tools: Read, Write, WebFetch, mcp__confluence__get_page, mcp__confluence__search, Bash
---

# SDLC Stage 1 · Requirements Ingestion

You are running Stage 1 of the SDLC automation pipeline.

## Input
The user will provide one of:
- A Confluence page URL → use `mcp__confluence__get_page` to fetch it
- A local file path (`.docx`, `.pdf`, `.md`) → use `Read` to load it
- A Confluence search query → use `mcp__confluence__search` first

Arguments: $ARGUMENTS

## Your Tasks

### 1. Fetch the requirements
- If the argument is a URL containing `confluence` or `atlassian`, call the Confluence MCP tool to retrieve the full page body.
- If it's a local file, read it directly.
- If it looks like a search term, search Confluence and present matching pages for the user to confirm before fetching.

### 2. Parse and structure
Extract from the document:
- **Epic / Feature name**
- **User stories** (as-a / I-want / so-that format)
- **Acceptance criteria** (bullet points or Given/When/Then)
- **Non-functional requirements** (performance, security, accessibility)
- **Out of scope** items explicitly mentioned
- **Dependencies** on other systems or teams

### 3. Identify gaps & ambiguities
For every requirement that is vague, contradictory, or missing detail, generate a numbered clarifying question. Format:
```
Q1. [Section] — <specific question>
Q2. [Section] — <specific question>
```

### 4. Present findings
Output a clean summary to the terminal, then ask the user to answer the questions inline or confirm they'll follow up async.

### 5. Save state
Once the user confirms or provides answers, write `.claude/sdlc-state.json`:

```json
{
  "stage": "ingest",
  "source": "<url or filename>",
  "epic": "<epic name>",
  "stories": [...],
  "acceptance_criteria": [...],
  "nfr": [...],
  "out_of_scope": [...],
  "open_questions": [...],
  "answered_questions": [...],
  "timestamp": "<ISO timestamp>"
}
```

## Done Condition
State file written. Print:
```
✅ Stage 1 complete. Run /sdlc-plan to generate Jira cards.
```
