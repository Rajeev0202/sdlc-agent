#!/usr/bin/env node
// Fires before any Bash(git push*) call.
// Reads coverage_pct from sdlc-state.json and blocks the push if below 80%.
// Exit code 1 = Claude Code will abort the tool call and show the error message.

const fs = require('fs');
const path = require('path');

const STATE = path.join(process.cwd(), '.claude', 'sdlc-state.json');
const THRESHOLD = 80;

let raw = '';
process.stdin.on('data', d => (raw += d));
process.stdin.on('end', () => {
  try {
    if (!fs.existsSync(STATE)) process.exit(0);

    const state = JSON.parse(fs.readFileSync(STATE, 'utf8'));
    const coverage = state.coverage_pct;

    // Only gate when we're in a build/commit stage and coverage was measured
    if (coverage === undefined || coverage === null) {
      console.log('[SDLC] Coverage gate: no measurement recorded — skipping.');
      process.exit(0);
    }

    if (coverage < THRESHOLD) {
      console.error(
        `[SDLC] PUSH BLOCKED: coverage is ${coverage}% (minimum ${THRESHOLD}%).\n` +
        `       Fix failing tests or add coverage, then retry.\n` +
        `       Run: /sdlc fix`
      );
      process.exit(1); // Non-zero exit blocks the git push tool call
    }

    console.log(`[SDLC] Coverage gate passed: ${coverage}% ≥ ${THRESHOLD}%`);
  } catch (_) {
    // Parse error — don't block the push
  }
  process.exit(0);
});
