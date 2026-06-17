#!/usr/bin/env node
// Stop — fires when Claude finishes a turn.
// 1. Appends an audit history entry to sdlc-state.json.
// 2. Updates stage-level run count + duration in metrics.json.
// 3. Prints the SDLC pipeline status banner.

const fs   = require('fs');
const path = require('path');

const STATE   = path.join(process.cwd(), '.claude', 'sdlc-state.json');
const OBS_DIR = path.join(process.cwd(), '.claude', 'observability');
const METRICS = path.join(OBS_DIR, 'metrics.json');

const PIPELINE = [
  ['ingest',    'Winston'], ['clarify',   'Winston'],
  ['plan',      'Priya'],   ['breakdown', 'Priya'],
  ['sprint',    'Marcus'],
  ['build',     'Amelia'],  ['commit',    'Amelia'],  ['pr',     'Amelia'],
  ['qa',        'Quinn'],   ['review',    'Devon'],    ['fix',    'Devon'],
];

function badge(currentStage, candidate) {
  const stages = PIPELINE.map(p => p[0]);
  const ci = stages.indexOf(currentStage);
  const ca = stages.indexOf(candidate);
  if (ca < ci)  return '✅';
  if (ca === ci) return '⏳';
  return '⬜';
}

function loadMetrics() {
  try { return JSON.parse(fs.readFileSync(METRICS, 'utf8')); } catch (_) { return {}; }
}

function saveMetrics(m) {
  if (!fs.existsSync(OBS_DIR)) fs.mkdirSync(OBS_DIR, { recursive: true });
  m.last_updated = new Date().toISOString();
  fs.writeFileSync(METRICS, JSON.stringify(m, null, 2));
}

let raw = '';
process.stdin.on('data', d => (raw += d));
process.stdin.on('end', () => {
  try {
    if (!fs.existsSync(STATE)) process.exit(0);

    const state = JSON.parse(fs.readFileSync(STATE, 'utf8'));
    const now   = new Date().toISOString();

    // ── Audit history ─────────────────────────────────────────────────────
    state.history = state.history || [];
    const histEntry = {
      stage:   state.stage,
      persona: state.persona || null,
      card:    state.current_card || null,
      ts:      now,
    };
    state.history.push(histEntry);
    fs.writeFileSync(STATE, JSON.stringify(state, null, 2));

    // ── Metrics: stage-level run count ────────────────────────────────────
    if (state.stage) {
      const metrics   = loadMetrics();
      metrics.totals  = metrics.totals || {};
      metrics.totals.agents_stopped = (metrics.totals.agents_stopped || 0) + 1;

      metrics.by_stage = metrics.by_stage || {};
      const s = metrics.by_stage[state.stage] = metrics.by_stage[state.stage] || {};
      s.runs  = (s.runs || 0) + 1;

      // Stage wall-clock: diff between first history entry for this stage and now
      const stageEntries = state.history.filter(h => h.stage === state.stage);
      if (stageEntries.length >= 2) {
        const wallMs = Date.parse(now) - Date.parse(stageEntries[0].ts);
        s.last_wall_ms  = wallMs;
      }

      saveMetrics(metrics);
    }

    // ── Status banner ─────────────────────────────────────────────────────
    const b   = s => badge(state.stage, s);
    const sep = '─'.repeat(52);
    const lines = [
      sep,
      `  SDLC · ${state.epic?.summary || 'No active session'}`,
      sep,
      `  ${b('ingest')} ingest  ${b('clarify')} clarify`,
      `  ${b('plan')} plan    ${b('breakdown')} breakdown  ${b('sprint')} sprint`,
      `  ${b('build')} build   ${b('commit')} commit     ${b('pr')} pr`,
      `  ${b('qa')} qa      ${b('review')} review     ${b('fix')} fix`,
      sep,
    ];
    if (state.current_card) lines.push(`  Card:   ${state.current_card}`);
    if (state.branch)       lines.push(`  Branch: ${state.branch}`);
    if (state.pr_url)       lines.push(`  PR:     ${state.pr_url}`);

    const stageErrors = (state.errors || []).filter(e => e.stage === state.stage);
    if (stageErrors.length > 0) {
      const last = stageErrors[stageErrors.length - 1];
      lines.push(`  Errors: ${stageErrors.length} this stage (last: ${last.tool})`);
    }

    lines.push(sep);
    lines.push(`  Observability: node .claude/hooks/sdlc-observe.js`);
    lines.push(sep);

    console.log(lines.join('\n'));
  } catch (_) {
    // Non-fatal — never block Claude on hook failure
  }
  process.exit(0);
});
