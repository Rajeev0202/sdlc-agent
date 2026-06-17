#!/usr/bin/env node
// Fires after every mcp__claude_ai_Atlassian_Rovo__createJiraIssue call.
// Logs the created card key into sdlc-state.json's jira_creates audit array.

const fs = require('fs');
const path = require('path');

const STATE = path.join(process.cwd(), '.claude', 'sdlc-state.json');

let raw = '';
process.stdin.on('data', d => (raw += d));
process.stdin.on('end', () => {
  try {
    const event = JSON.parse(raw);

    let response = event.tool_response;
    if (typeof response === 'string') {
      try { response = JSON.parse(response); } catch (_) { response = {}; }
    }

    // Jira MCP returns { key, id, self } on creation
    const key = response?.key || response?.id;
    if (!key) process.exit(0);

    if (!fs.existsSync(STATE)) process.exit(0);
    const state = JSON.parse(fs.readFileSync(STATE, 'utf8'));

    state.jira_creates = state.jira_creates || [];
    state.jira_creates.push({
      key,
      summary: event.tool_input?.fields?.summary || null,
      parent:  event.tool_input?.fields?.parent?.key || event.tool_input?.fields?.parent?.id || null,
      confluence_url: state.confluence_url || null,
      ts: new Date().toISOString(),
    });

    fs.writeFileSync(STATE, JSON.stringify(state, null, 2));
    console.log(`[SDLC] Jira card logged: ${key}`);
  } catch (_) {
    // Non-fatal — never block Claude on hook failure
  }
  process.exit(0);
});
