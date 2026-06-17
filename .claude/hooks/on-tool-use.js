#!/usr/bin/env node
// PostToolUse — fires after every tool call.
// Observability pillars written here:
//   TRACES  → .claude/observability/traces.jsonl  (one span per tool call)
//   LOGS    → .claude/observability/logs.jsonl    (INFO / WARN / ERROR entries)
//   METRICS → .claude/observability/metrics.json  (aggregated counters, updated in-place)
// Also keeps the legacy sdlc-trace.jsonl and state.errors[] for backwards compat.

const fs   = require('fs');
const path = require('path');

const OBS_DIR    = path.join(process.cwd(), '.claude', 'observability');
const TRACES     = path.join(OBS_DIR, 'traces.jsonl');
const LOGS       = path.join(OBS_DIR, 'logs.jsonl');
const METRICS    = path.join(OBS_DIR, 'metrics.json');
const LEGACY_TRACE = path.join(process.cwd(), '.claude', 'sdlc-trace.jsonl');
const STATE      = path.join(process.cwd(), '.claude', 'sdlc-state.json');
const START_FILE = path.join(process.cwd(), '.claude', '.tool-start.json');

const ERROR_PATTERNS = /\b(error|exception|failed|failure|traceback|cannot|not found|permission denied|enoent|eacces|command not found|exit code [^0])\b/i;

function isErrorResponse(response) {
  if (response == null) return false;
  const text = typeof response === 'string' ? response : JSON.stringify(response);
  return ERROR_PATTERNS.test(text);
}

function summarise(input) {
  if (!input) return null;
  if (input.command) return String(input.command).slice(0, 120);
  const first = Object.values(input)[0];
  if (first == null) return null;
  const str = typeof first === 'object' ? JSON.stringify(first) : String(first);
  return str.slice(0, 120);
}

function loadMetrics() {
  try { return JSON.parse(fs.readFileSync(METRICS, 'utf8')); } catch (_) { return {}; }
}

function saveMetrics(m) {
  m.last_updated = new Date().toISOString();
  fs.writeFileSync(METRICS, JSON.stringify(m, null, 2));
}

function updateMetrics(m, { stage, tool, duration_ms, success }) {
  // Totals
  m.totals             = m.totals             || {};
  m.totals.tool_calls  = (m.totals.tool_calls  || 0) + 1;
  m.totals.errors      = (m.totals.errors      || 0) + (success ? 0 : 1);
  m.totals.error_rate_pct = m.totals.tool_calls
    ? +((m.totals.errors / m.totals.tool_calls) * 100).toFixed(2)
    : 0;

  // By stage
  if (stage) {
    m.by_stage        = m.by_stage || {};
    const s           = m.by_stage[stage] = m.by_stage[stage] || {};
    s.tool_calls      = (s.tool_calls || 0) + 1;
    s.errors          = (s.errors || 0) + (success ? 0 : 1);
    s.error_rate_pct  = +((s.errors / s.tool_calls) * 100).toFixed(2);
    if (duration_ms != null) {
      s.total_duration_ms   = (s.total_duration_ms || 0) + duration_ms;
      s.avg_tool_duration_ms = +(s.total_duration_ms / s.tool_calls).toFixed(0);
    }
  }

  // By tool
  if (tool) {
    m.by_tool    = m.by_tool || {};
    const t      = m.by_tool[tool] = m.by_tool[tool] || {};
    t.calls      = (t.calls || 0) + 1;
    t.errors     = (t.errors || 0) + (success ? 0 : 1);
    if (duration_ms != null) {
      t.total_duration_ms = (t.total_duration_ms || 0) + duration_ms;
      t.avg_duration_ms   = +(t.total_duration_ms / t.calls).toFixed(0);
    }
  }
}

let raw = '';
process.stdin.on('data', d => (raw += d));
process.stdin.on('end', () => {
  try {
    const event = JSON.parse(raw);

    if (!fs.existsSync(OBS_DIR)) fs.mkdirSync(OBS_DIR, { recursive: true });

    // Read start metadata (trace_id, span_id, start timestamp)
    let trace_id = null, span_id = null, duration_ms = null;
    try {
      const start = JSON.parse(fs.readFileSync(START_FILE, 'utf8'));
      if (start.tool === event.tool_name) {
        duration_ms = Date.now() - start.ts;
        trace_id    = start.trace_id || null;
        span_id     = start.span_id  || null;
      }
    } catch (_) {}

    const success = !isErrorResponse(event.tool_response);

    // State context
    let state = {};
    try { state = JSON.parse(fs.readFileSync(STATE, 'utf8')); } catch (_) {}

    const now   = new Date().toISOString();
    const stage = state.stage   || null;
    const persona = state.persona || null;
    const card  = state.current_card || null;

    // ── TRACES ───────────────────────────────────────────────────────────────
    const span = {
      trace_id,
      span_id,
      ts:          now,
      stage,
      persona,
      card,
      tool:        event.tool_name,
      input:       summarise(event.tool_input),
      duration_ms,
      status:      success ? 'ok' : 'error',
    };
    fs.appendFileSync(TRACES, JSON.stringify(span) + '\n');

    // ── LOGS ─────────────────────────────────────────────────────────────────
    const responseText = typeof event.tool_response === 'string'
      ? event.tool_response
      : JSON.stringify(event.tool_response || '');

    const level = success ? 'INFO' : 'ERROR';
    const logEntry = {
      ts:      now,
      level,
      trace_id,
      span_id,
      stage,
      persona,
      card,
      tool:    event.tool_name,
      message: success
        ? `${event.tool_name} completed in ${duration_ms ?? '?'}ms`
        : `${event.tool_name} failed — ${responseText.slice(0, 120)}`,
    };
    if (!success) logEntry.snippet = responseText.slice(0, 300);
    fs.appendFileSync(LOGS, JSON.stringify(logEntry) + '\n');

    // ── METRICS ──────────────────────────────────────────────────────────────
    const metrics = loadMetrics();
    updateMetrics(metrics, { stage, tool: event.tool_name, duration_ms, success });
    saveMetrics(metrics);

    // ── LEGACY sdlc-trace.jsonl ───────────────────────────────────────────────
    fs.appendFileSync(LEGACY_TRACE, JSON.stringify({
      ts: now, trace_id, span_id, stage, persona, card,
      tool: event.tool_name,
      input: summarise(event.tool_input),
      duration_ms, success,
    }) + '\n');

    // ── STATE errors[] ────────────────────────────────────────────────────────
    if (!success) {
      state.errors = state.errors || [];
      state.errors.push({ ...span, snippet: responseText.slice(0, 300) });
      fs.writeFileSync(STATE, JSON.stringify(state, null, 2));
    }
  } catch (_) {
    // Non-fatal — never block Claude on hook failure
  }
  process.exit(0);
});
