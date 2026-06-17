#!/usr/bin/env node
// SDLC Observability Report CLI
//
// Usage:
//   node .claude/hooks/sdlc-observe.js            → full summary report
//   node .claude/hooks/sdlc-observe.js metrics    → aggregated metrics dashboard
//   node .claude/hooks/sdlc-observe.js traces [N] → last N spans (default 20)
//   node .claude/hooks/sdlc-observe.js logs [N]   → last N log entries (default 20)
//   node .claude/hooks/sdlc-observe.js errors     → all ERROR log entries
//   node .claude/hooks/sdlc-observe.js slow [N]   → top N slowest tool calls (default 10)
//   node .claude/hooks/sdlc-observe.js trace <trace_id> → all spans for a trace

const fs   = require('fs');
const path = require('path');

const OBS_DIR = path.join(process.cwd(), '.claude', 'observability');
const TRACES  = path.join(OBS_DIR, 'traces.jsonl');
const LOGS    = path.join(OBS_DIR, 'logs.jsonl');
const METRICS = path.join(OBS_DIR, 'metrics.json');

// ── Helpers ──────────────────────────────────────────────────────────────────

function readJsonl(file) {
  if (!fs.existsSync(file)) return [];
  return fs.readFileSync(file, 'utf8')
    .split('\n')
    .filter(Boolean)
    .map(line => { try { return JSON.parse(line); } catch (_) { return null; } })
    .filter(Boolean);
}

function loadMetrics() {
  if (!fs.existsSync(METRICS)) return null;
  try { return JSON.parse(fs.readFileSync(METRICS, 'utf8')); } catch (_) { return null; }
}

function fmtMs(ms) {
  if (ms == null) return '—';
  if (ms < 1000)  return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function fmtNum(n) {
  if (n == null) return '—';
  return n.toLocaleString();
}

function pad(str, len, right = false) {
  const s = String(str ?? '—');
  return right ? s.padStart(len) : s.padEnd(len);
}

const SEP  = '━'.repeat(60);
const SEP2 = '─'.repeat(60);

// ── Commands ──────────────────────────────────────────────────────────────────

function cmdMetrics() {
  const m = loadMetrics();
  if (!m) { console.log('No metrics recorded yet. Run any /sdlc stage first.'); return; }

  console.log('\n' + SEP);
  console.log('  SDLC Metrics Dashboard');
  console.log(`  Last updated: ${m.last_updated ?? '—'}`);
  console.log(SEP);

  // Totals
  const t = m.totals || {};
  console.log('\n  ── Totals ──────────────────────────────────────────');
  console.log(`  Tool calls:    ${fmtNum(t.tool_calls)}`);
  console.log(`  Errors:        ${fmtNum(t.errors)}  (${t.error_rate_pct ?? 0}%)`);
  console.log(`  Agents stopped:${fmtNum(t.agents_stopped)}`);

  // By stage
  if (m.by_stage && Object.keys(m.by_stage).length) {
    console.log('\n  ── By Stage ────────────────────────────────────────');
    console.log(`  ${pad('Stage', 12)} ${pad('Runs', 5, true)} ${pad('Calls', 6, true)} ${pad('Errors', 6, true)} ${pad('Err%', 6, true)} ${pad('Avg Tool', 9, true)}`);
    console.log('  ' + SEP2.slice(0, 56));
    for (const [stage, s] of Object.entries(m.by_stage)) {
      console.log(`  ${pad(stage, 12)} ${pad(s.runs, 5, true)} ${pad(s.tool_calls, 6, true)} ${pad(s.errors, 6, true)} ${pad((s.error_rate_pct ?? 0) + '%', 6, true)} ${pad(fmtMs(s.avg_tool_duration_ms), 9, true)}`);
    }
  }

  // By tool
  if (m.by_tool && Object.keys(m.by_tool).length) {
    console.log('\n  ── By Tool ─────────────────────────────────────────');
    console.log(`  ${pad('Tool', 40)} ${pad('Calls', 6, true)} ${pad('Errors', 6, true)} ${pad('Avg', 8, true)}`);
    console.log('  ' + SEP2.slice(0, 60));
    const sorted = Object.entries(m.by_tool).sort((a, b) => (b[1].calls || 0) - (a[1].calls || 0));
    for (const [tool, s] of sorted) {
      console.log(`  ${pad(tool, 40)} ${pad(s.calls, 6, true)} ${pad(s.errors, 6, true)} ${pad(fmtMs(s.avg_duration_ms), 8, true)}`);
    }
  }

  console.log('\n' + SEP + '\n');
}

function cmdTraces(n = 20) {
  const spans = readJsonl(TRACES).slice(-n);
  if (!spans.length) { console.log('No traces recorded yet.'); return; }

  console.log('\n' + SEP);
  console.log(`  SDLC Traces — last ${spans.length} spans`);
  console.log(SEP);
  console.log(`  ${pad('Time', 24)} ${pad('Stage', 10)} ${pad('Tool', 30)} ${pad('Status', 7)} ${pad('Duration', 9, true)}`);
  console.log('  ' + SEP2);
  for (const s of spans) {
    const status = s.status === 'ok' ? 'ok    ' : 'ERROR ';
    console.log(`  ${pad(s.ts?.slice(0, 23), 24)} ${pad(s.stage, 10)} ${pad(s.tool, 30)} ${status} ${pad(fmtMs(s.duration_ms), 9, true)}`);
  }
  console.log('\n' + SEP + '\n');
}

function cmdLogs(n = 20) {
  const entries = readJsonl(LOGS).slice(-n);
  if (!entries.length) { console.log('No logs recorded yet.'); return; }

  console.log('\n' + SEP);
  console.log(`  SDLC Logs — last ${entries.length} entries`);
  console.log(SEP);
  for (const e of entries) {
    const lvl = e.level === 'ERROR' ? '[ERROR]' : '[INFO] ';
    console.log(`  ${e.ts?.slice(0, 23)} ${lvl} [${e.stage ?? '—'}] ${e.message}`);
    if (e.snippet) console.log(`         ↳ ${e.snippet.slice(0, 100)}`);
  }
  console.log('\n' + SEP + '\n');
}

function cmdErrors() {
  const all    = readJsonl(LOGS);
  const errors = all.filter(e => e.level === 'ERROR');
  if (!errors.length) { console.log('No errors recorded. ✅'); return; }

  console.log('\n' + SEP);
  console.log(`  SDLC Errors — ${errors.length} total`);
  console.log(SEP);
  for (const e of errors) {
    console.log(`\n  ${e.ts?.slice(0, 23)} [${e.stage ?? '—'}] [${e.persona ?? '—'}]`);
    console.log(`  Tool:    ${e.tool}`);
    console.log(`  Message: ${e.message}`);
    if (e.snippet) console.log(`  Snippet: ${e.snippet.slice(0, 150)}`);
    if (e.trace_id) console.log(`  Trace:   ${e.trace_id}  Span: ${e.span_id}`);
  }
  console.log('\n' + SEP + '\n');
}

function cmdSlow(n = 10) {
  const spans = readJsonl(TRACES)
    .filter(s => s.duration_ms != null)
    .sort((a, b) => b.duration_ms - a.duration_ms)
    .slice(0, n);

  if (!spans.length) { console.log('No trace data yet.'); return; }

  console.log('\n' + SEP);
  console.log(`  SDLC Slowest Tool Calls — top ${spans.length}`);
  console.log(SEP);
  console.log(`  ${pad('Duration', 9, true)} ${pad('Stage', 10)} ${pad('Tool', 30)} ${pad('Status', 6)} ${pad('Input', 30)}`);
  console.log('  ' + SEP2);
  for (const s of spans) {
    console.log(`  ${pad(fmtMs(s.duration_ms), 9, true)} ${pad(s.stage, 10)} ${pad(s.tool, 30)} ${pad(s.status, 6)} ${pad(s.input?.slice(0, 30) ?? '—', 30)}`);
  }
  console.log('\n' + SEP + '\n');
}

function cmdTraceById(traceId) {
  const spans = readJsonl(TRACES).filter(s => s.trace_id === traceId);
  if (!spans.length) { console.log(`No spans found for trace_id: ${traceId}`); return; }

  console.log('\n' + SEP);
  console.log(`  Trace: ${traceId}   (${spans.length} spans)`);
  console.log(SEP);
  for (const s of spans) {
    const status = s.status === 'ok' ? '✅' : '❌';
    console.log(`  ${status} ${pad(fmtMs(s.duration_ms), 8, true)}  ${pad(s.tool, 30)}  ${s.input?.slice(0, 40) ?? ''}`);
    console.log(`     span: ${s.span_id}  ts: ${s.ts?.slice(0, 23)}`);
  }
  const total = spans.reduce((sum, s) => sum + (s.duration_ms || 0), 0);
  const errs  = spans.filter(s => s.status !== 'ok').length;
  console.log(SEP2);
  console.log(`  Total measured: ${fmtMs(total)}   Errors: ${errs}/${spans.length}`);
  console.log('\n' + SEP + '\n');
}

function cmdSummary() {
  // Full report: metrics + recent errors + slowest tools
  cmdMetrics();
  cmdErrors();
  cmdSlow(5);
}

// ── Entry point ───────────────────────────────────────────────────────────────

const [,, cmd, arg] = process.argv;

switch (cmd) {
  case 'metrics': cmdMetrics();              break;
  case 'traces':  cmdTraces(Number(arg) || 20);  break;
  case 'logs':    cmdLogs(Number(arg) || 20);    break;
  case 'errors':  cmdErrors();              break;
  case 'slow':    cmdSlow(Number(arg) || 10);    break;
  case 'trace':
    if (!arg) { console.log('Usage: sdlc-observe.js trace <trace_id>'); break; }
    cmdTraceById(arg);
    break;
  default:        cmdSummary();             break;
}
