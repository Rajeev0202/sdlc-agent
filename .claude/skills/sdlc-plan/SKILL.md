---
description: SDLC Stage 2 — Read confirmed requirements from sdlc-state.json and create Jira user story cards with acceptance criteria, story points, and labels. Invoke with /sdlc-plan <jira-project-key>.
allowed-tools: Read, Write, mcp__claude_ai_Atlassian_Rovo__createJiraIssue, mcp__claude_ai_Atlassian_Rovo__getVisibleJiraProjects, mcp__claude_ai_Atlassian_Rovo__getJiraProjectIssueTypesMetadata, Bash
---

# SDLC Stage 2 · Jira Card Generation

You are running Stage 2 of the SDLC automation pipeline.

## Pre-check
Read `.claude/sdlc-state.json`. If `stage` is not `"ingest"`, stop and tell the user to run `/sdlc-ingest` first.

If `open_questions` has unanswered items, warn the user and ask if they want to proceed anyway.

## Input
Arguments: $ARGUMENTS (expected: Jira project key, e.g. `PROJ`)

---

## Step 1 · Load requirements
Read all confirmed stories and acceptance criteria from the state file's `requirements` array.

---

## Step 2 · Decompose each requirement into multiple stories

For **every** requirement, analyse the text and acceptance criteria to identify distinct work units. Apply the following decomposition rules:

### 2a · Split by microservice / module
If a requirement touches more than one microservice, backend service, or bounded context, create **one story per service/module**. Name each story clearly:
- `[ServiceName] <short description>`
- Example: `[OrderService] Add discount validation endpoint` and `[InventoryService] Expose stock-check API`

### 2b · Split by layer (API vs UI)
If a requirement involves both a backend API change and a frontend/UI change, create **separate stories**:
- One story for the API layer (tagged `layer:api`)
- One story for the UI/frontend layer (tagged `layer:ui`)
- Add a story link between them noting the dependency (API → UI)

### 2c · Split by integration boundary
If a requirement involves third-party integrations, event publishing, or database migrations that are independently deployable, break these out as separate stories.

### Rule of thumb
A story should represent work that can be implemented, reviewed, and deployed independently. If two things have different owners, different repos, or different deployment cycles — they are different stories.

---

## Step 3 · Write each story card

For every story produced by Step 2, prepare the following fields.

### Summary
Concise, ≤ 72 characters. Prefix with `[ServiceName]` or `[API]` / `[UI]` when applicable.

### Description
**CRITICAL FORMATTING RULE:** Jira does not render `\n` escape sequences. You MUST write the description as a real multi-line string using actual line breaks. Use Jira Wiki Markup syntax:

```
h3. User Story
As a <role>, I want <goal>, so that <benefit>.

h3. Acceptance Criteria
*Given* <context>
*When* <action>
*Then* <expected outcome>

*Given* <context 2>
*When* <action 2>
*Then* <expected outcome 2>

h3. Definition of Done
* Unit tests written (TDD — red first)
* Integration tests passing
* Code reviewed and approved
* Deployed to staging
* Acceptance criteria verified by PO
```

Rules:
- Use `h3.` for section headings (renders as bold heading in Jira UI)
- Use `*text*` for bold inline text
- Use `* item` for bullet lists (space after `*`)
- Use `# item` for numbered lists
- Separate every section with a blank line
- Write **minimum 3 Given/When/Then scenarios**
- Never concatenate the whole description onto one line

### Story Points
Fibonacci scale (1, 2, 3, 5, 8, 13):
- 1–2: trivial config or copy change
- 3–5: standard feature with tests
- 8–13: cross-cutting, uncertain, or multi-service coordination

### Labels
Always include: `ai-generated`, `tdd`
Add as applicable: `layer:api`, `layer:ui`, `microservice:<name>`, and any domain tags from requirements.

### Priority
Set based on dependency order:
- Stories that others depend on → `High`
- Independent feature stories → `Medium`
- Cleanup / refactor stories → `Low`

---

## Step 4 · Define sub-tasks for each story

Create sub-tasks that reflect the actual work needed. Do **not** use generic TEST/IMPL/REFACTOR boilerplate for every story — tailor sub-tasks to the story's layer and complexity.

### For an API story, the sub-tasks are:
1. `[TEST] Write failing contract/unit tests for <story summary>`
2. `[IMPL] Implement endpoint / service logic for <story summary>`
3. `[IMPL] Write integration tests against real DB/service`
4. `[REFACTOR] Refactor and clean up <story summary>`
5. `[DOCS] Update API documentation / OpenAPI spec`

### For a UI story, the sub-tasks are:
1. `[TEST] Write failing component/E2E tests for <story summary>`
2. `[IMPL] Build UI components for <story summary>`
3. `[IMPL] Wire API integration and error states`
4. `[REFACTOR] Refactor and clean up <story summary>`
5. `[UX] Verify against design specs / accessibility checklist`

### For a full-stack story (not split), the sub-tasks are:
1. `[TEST] Write failing API tests for <story summary>`
2. `[IMPL] Implement backend logic for <story summary>`
3. `[TEST] Write failing UI tests for <story summary>`
4. `[IMPL] Build frontend for <story summary>`
5. `[REFACTOR] Refactor and clean up <story summary>`

### For a migration / infra story, the sub-tasks are:
1. `[TEST] Write migration rollback test`
2. `[IMPL] Write and validate migration script`
3. `[IMPL] Update service to use new schema/config`
4. `[VERIFY] Run migration on staging and confirm data integrity`

---

## Step 5 · Create Jira issues

For each story:
1. Call `mcp__claude_ai_Atlassian_Rovo__createJiraIssue` with `issuetype: "Story"` and the prepared fields.
2. Capture the returned card ID and URL.
3. For each sub-task, call `mcp__claude_ai_Atlassian_Rovo__createJiraIssue` with `issuetype: "Sub-task"` and `parent: <story card ID>`.

Create all stories first, then all sub-tasks in a second pass so parent IDs are known.

---

## Step 6 · Update state file

Write the updated state to `.claude/sdlc-state.json`:

```json
{
  "stage": "plan",
  "jira_project": "<key>",
  "cards": [
    {
      "id": "PROJ-42",
      "summary": "[API] Add discount validation endpoint",
      "points": 5,
      "labels": ["ai-generated", "tdd", "layer:api"],
      "url": "https://...",
      "subtasks": ["PROJ-43", "PROJ-44", "PROJ-45"]
    }
  ]
}
```

---

## Done Condition

Print a summary table grouped by requirement:

```
Requirement 1: <requirement title>
  PROJ-42  [API] Add discount validation endpoint      5pts  https://...
    PROJ-43  [TEST] Write failing contract tests        -
    PROJ-44  [IMPL] Implement endpoint logic            -
  PROJ-46  [UI] Build discount entry UI                 3pts  https://...
    PROJ-47  [TEST] Write failing component tests       -
    PROJ-48  [IMPL] Build UI components                 -
```

Then print:
```
✅ Stage 2 complete. Run /sdlc-build <CARD-ID> to start implementation.
```
