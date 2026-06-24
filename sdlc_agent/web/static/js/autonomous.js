// SDLC Agent · Autonomous pipeline (run + resume) and escapeHtml
// Classic (non-module) script — globals shared across files; load order matters.

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

// ---- Autonomous Pipeline (runs Stages 1-2, halts at PO gate, then resumes) ----
async function autonomous() {
  const confluenceUrlEl = document.getElementById("confluence-url");
  const source = confluenceUrlEl.value.trim() || "samples/brd_natwest_card_freeze.md";

  // PHASE 1: Run Stages 1-2 and halt at PO approval gate
  // Sequential UI updates - Stage 1 first, then Stage 2
  setStatus(1, "Running…", "running");
  showNotification("🤖 Phase 1: Stage 1 (Ingest) starting...", "info");

  // Stage 2 begins when Stage 1 likely completes (~2-3 seconds in)
  const stage2Timer = setTimeout(() => {
    setStatus(1, "Complete", "done");
    setStatus(2, "Running…", "running");
    showNotification("Stage 1 done → Stage 2 (Plan) starting...", "info");
  }, 3000);

  const phase1 = await post("/api/autonomous-pipeline", { source, auto_approve: false });
  clearTimeout(stage2Timer);  // cancel timer if response came back first
  console.log("[Autonomous] Phase 1 response:", phase1);

  // Try multiple paths to find run_id
  const runId = phase1.final_output?.run_id
                || phase1.run_id
                || phase1.history?.find(h => h.run_id)?.run_id;

  if (!runId) {
    console.error("[Autonomous] No run_id in Phase 1 response:", phase1);
    throw new Error(`Phase 1 did not return a run_id. Response: ${JSON.stringify(phase1).slice(0, 200)}`);
  }

  state.run_id = runId;
  const runIdEl = document.getElementById("run-id");
  if (runIdEl) runIdEl.textContent = runId;
  console.log("[Autonomous] Set state.run_id =", runId);

  // Render Stage 1 brief
  if (phase1.brief) {
    const b = phase1.brief;
    show(1, `
      <p><strong>✓ Requirements Ingested</strong> <span class="chip chip-ok">🤖 Autonomous</span></p>
      <p>Run ID: <code>${runId}</code></p>
      <table>
        <tr><th>Title</th><td>${b.title || 'N/A'}</td></tr>
        <tr><th>Business goal</th><td>${b.business_goal || 'N/A'}</td></tr>
        <tr><th>Personas (${(b.personas||[]).length})</th><td>${(b.personas||[]).map(p=>`<span class="chip">${p.name}</span>`).join("")}</td></tr>
        <tr><th>Functional needs (${(b.functional_needs||[]).length})</th><td><ul>${(b.functional_needs||[]).map(x=>`<li>${x}</li>`).join("")}</ul></td></tr>
        <tr><th>Non-functional (${(b.non_functional_constraints||[]).length})</th><td><ul>${(b.non_functional_constraints||[]).map(x=>`<li>${x}</li>`).join("")}</ul></td></tr>
        <tr><th>Open questions</th><td>${(b.open_questions||[]).length ? '<ul>' + b.open_questions.map(q=>`<li>${q}</li>`).join("") + '</ul>' : "<em>none</em>"}</td></tr>
      </table>
    `);
  }

  // Render Stage 2 stories
  if (phase1.backlog) {
    const stories = phase1.backlog.stories || [];
    const rows = stories.map(s => `
      <tr>
        <td><strong>${s.id}</strong></td>
        <td>—</td>
        <td>${s.as_a_statement || `As a ${s.persona}, I want ${s.want}, so that ${s.so_that}.`}</td>
        <td>${(s.acceptance_criteria || []).length}</td>
        <td>${(s.dependencies||[]).map(d=>`<span class="chip">${d}</span>`).join("") || "—"}</td>
      </tr>`).join("");
    show(2, `
      <p><strong>✓ ${stories.length} User Stories Generated</strong> <span class="chip chip-ok">🤖 Autonomous</span></p>
      <table><tr><th>ID</th><th>Jira</th><th>Story</th><th>ACs</th><th>Dependencies</th></tr>${rows}</table>
      <p class="info">⏸️ Pipeline paused at PO approval gate. Approve below to continue with Stages 3-6.</p>
    `);
  }

  setStatus(1, "Complete", "done");
  setStatus(2, "Awaiting PO", "running");

  // Show PO approval gate
  document.getElementById("po-gate").hidden = false;

  // Mark approve button to trigger phase 2
  const approveBtn = document.querySelector('button[data-action="approve"]');
  if (approveBtn) {
    approveBtn.dataset.autonomousMode = "true";
  }

  showNotification("⏸️ Pipeline halted at PO approval gate. Please approve to continue.", "warning");
}

// ---- Resume autonomous pipeline after PO approval ----
async function resumeAutonomous() {
  // Sequential UI updates - light up stages one at a time
  setStatus(3, "Running…", "running");
  showNotification("▶️ Phase 2: Stage 3 (Build) starting...", "info");

  // Stagger status updates to give visual progress feedback
  const timers = [];
  timers.push(setTimeout(() => {
    setStatus(3, "Complete", "done");
    setStatus(4, "Running…", "running");
    showNotification("Stage 3 done → Stage 4 (Review) starting...", "info");
  }, 4000));
  timers.push(setTimeout(() => {
    setStatus(4, "Complete", "done");
    setStatus(5, "Running…", "running");
    showNotification("Stage 4 done → Stage 5 (Test) starting...", "info");
  }, 8000));
  timers.push(setTimeout(() => {
    setStatus(5, "Complete", "done");
    setStatus(6, "Running…", "running");
    showNotification("Stage 5 done → Stage 6 (Deploy) starting...", "info");
  }, 14000));

  const phase2 = await post("/api/autonomous-pipeline-resume", { run_id: state.run_id });
  timers.forEach(t => clearTimeout(t));  // clean up pending timers

  // Render Phase 2 history
  const phase2HistoryHtml = (phase2.history || []).map(h => {
    const iter = h.iterations ? ` (×${h.iterations} iterations)` : '';
    return `<li><strong>Stage ${h.stage || '?'}</strong>: ${h.status || h.verdict || h.decision || JSON.stringify(h)}${iter}</li>`;
  }).join('');

  const decision = phase2.final_output?.decision;
  const decisionBadge = decision
    ? `<span class="${decision.go ? 'verdict-go' : 'verdict-nogo'}">${decision.go ? 'GO ✅' : 'NO-GO ❌'}</span>`
    : '';

  show(6, `
    <p><strong>🤖 Autonomous Pipeline Complete ${phase2.status === 'success' ? '✅' : phase2.status === 'failed' ? '❌' : '⚠️'}</strong> ${decisionBadge}</p>
    <p>Status: <code>${phase2.status}</code> | Duration: ${(phase2.duration_ms / 1000).toFixed(1)}s</p>
    ${phase2.error ? `<p class="fail">Error: ${phase2.error}</p>` : ''}
    <details open><summary>📋 Phase 2 History (${(phase2.history || []).length} steps)</summary>
      <ol>${phase2HistoryHtml}</ol>
    </details>
  `);

  // Set Stage 3-6 to complete
  for (let i = 3; i <= 6; i++) {
    setStatus(i, "Auto-Complete", phase2.status === 'success' ? 'done' : 'warn');
  }

  if (phase2.status === 'success' && decision?.go) {
    showNotification("✅ Pipeline completed successfully (GO)", "success");
  } else {
    showNotification(`⚠️ Pipeline finished: ${phase2.status}`, "warning");
  }
}
