#!/usr/bin/env node
// PreToolUse — fires before every tool call.
// 1. Resolves or generates a trace_id for the current pipeline session.
// 2. Generates a unique span_id for this tool call.
// 3. Writes {tool, ts, trace_id, span_id} to .tool-start.json so
//    on-tool-use.js can close the span with duration + status.

const fs   = require('fs');
const path = require('path');

const STATE      = path.join(process.cwd(), '.claude', 'sdlc-state.json');
const START_FILE = path.join(process.cwd(), '.claude', '.tool-start.json');
const OBS_DIR    = path.join(process.cwd(), '.claude', 'observability');

function shortId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

let raw = '';
process.stdin.on('data', d => (raw += d));
process.stdin.on('end', () => {
  try {
    const event = JSON.parse(raw);

    // Ensure observability directory exists
    if (!fs.existsSync(OBS_DIR)) fs.mkdirSync(OBS_DIR, { recursive: true });

    // Resolve trace_id from state (one per pipeline session)
    let trace_id = null;
    let state    = {};
    try {
      state    = JSON.parse(fs.readFileSync(STATE, 'utf8'));
      trace_id = state.trace_id || null;
    } catch (_) {}

    if (!trace_id) {
      trace_id = 'trace-' + shortId();
      // Persist so all subsequent hooks share the same trace_id
      state.trace_id = trace_id;
      try { fs.writeFileSync(STATE, JSON.stringify(state, null, 2)); } catch (_) {}
    }

    const span_id = 'span-' + shortId();

    fs.writeFileSync(START_FILE, JSON.stringify({
      tool:     event.tool_name,
      ts:       Date.now(),
      trace_id,
      span_id,
    }));
  } catch (_) {}
  process.exit(0);
});
