// SDLC Agent — UI driver. Each stage button posts JSON to /api/stageN and
// renders the response into its card.

const state = {
  run_id: null,
  completedStages: 0,
  // Stage 5 workflow state
  stage5: {
    manualTestsGenerated: false,
    automationScriptsGenerated: false,
    testsExecuted: false,
    hasFailures: false
  }
};

function updateProgressBar() {
  // Update new pipeline progress fill
  const progress = (state.completedStages / 6) * 100;
  const fill = document.getElementById('pipeline-progress-fill');
  if (fill) {
    fill.style.width = `${progress}%`;
  }

  // Update completed count
  const countEl = document.getElementById('completed-count');
  if (countEl) {
    countEl.textContent = state.completedStages;
  }

  // Legacy support (if old progress bar exists)
  const oldBar = document.getElementById('progress-bar');
  if (oldBar) {
    oldBar.style.width = `${progress}%`;
  }
}

function setStatus(stage, label, cls) {
  const el = document.getElementById(`s${stage}-status`);
  if (!el) {
    console.warn(`Status element not found for stage ${stage}`);
    return;
  }
  el.textContent = label;
  el.className = `status ${cls}`;

  // Update progress when stage completes
  if (cls === 'done' && stage > state.completedStages) {
    state.completedStages = stage;
    updateProgressBar();
  }

  // Update pipeline tracker (new) and legacy cycle legend
  updatePipelineTracker(stage, cls);
  updateCycleLegend(stage, cls);
}

function updatePipelineTracker(stage, status) {
  const pipelineStage = document.querySelector(`.pipeline-stage[data-stage="${stage}"]`);
  if (!pipelineStage) return;

  // Remove previous status classes for this stage
  pipelineStage.classList.remove('active', 'completed', 'failed');

  if (status === 'done') {
    // Mark as completed (green light on)
    pipelineStage.classList.add('completed');
  } else if (status === 'fail') {
    // Mark as failed (red light on)
    pipelineStage.classList.add('failed');
  } else if (status === 'running' || status === 'pending') {
    // Mark as active (yellow pulsing light)
    if (status === 'running') {
      pipelineStage.classList.add('active');
    }
  }

  // Re-apply completed state to all previously completed stages
  for (let i = 1; i <= state.completedStages; i++) {
    const stageEl = document.querySelector(`.pipeline-stage[data-stage="${i}"]`);
    if (stageEl) {
      stageEl.classList.remove('active', 'failed');
      stageEl.classList.add('completed');
    }
  }
}

function updateCycleLegend(stage, status) {
  // Legacy: Remove active class from all legend items (if old UI elements exist)
  document.querySelectorAll('.legend-item').forEach(item => {
    item.classList.remove('active');
  });

  // Legacy: Add active class to current stage
  const currentLegendItem = document.querySelector(`.legend-item[data-stage="${stage}"]`);
  if (currentLegendItem && (status === 'running' || status === 'done')) {
    currentLegendItem.classList.add('active');
  }
}

function unlock(stage) {
  const card = document.getElementById(`stage${stage}`);
  if (!card) {
    console.warn(`Card not found for stage ${stage}`);
    return;
  }
  card.classList.remove("locked");

  // For Stage 5, only enable the first button (progressive workflow)
  if (stage === 5) {
    const manualBtn = document.querySelector('button[data-action="stage5-manual"]');
    if (manualBtn) manualBtn.disabled = false;
  } else {
    // For other stages, enable all buttons
    card.querySelectorAll("button[data-action]").forEach(b => b.disabled = false);
  }

  setStatus(stage, "Ready", "pending");

  // Smooth scroll to next stage
  setTimeout(() => {
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, 300);
}
function fileLink(path) {
  if (!path || path === 'N/A') {
    return '<span class="text-muted">N/A</span>';
  }
  return `<a class="file-link" href="/files/${path.replaceAll('\\\\', '/')}" target="_blank">${path}</a>`;
}
function show(stage, html) {
  // Support both old format (stage number) and new format (workflow step name)
  let el = document.getElementById(`s${stage}-out`);
  if (!el) {
    el = document.getElementById(`s5-${stage}-out`);
  }
  if (el) {
    el.innerHTML = html;
  } else {
    console.warn(`Output element not found for stage ${stage}`);
  }
}
async function post(url, body) {
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)
    });

    let j;
    try {
      j = await r.json();
    } catch (jsonError) {
      throw new Error(`Failed to parse response: ${r.statusText}`);
    }

    if (!r.ok) {
      throw new Error(j.error || `HTTP ${r.status}: ${r.statusText}`);
    }
    return j;
  } catch (error) {
    console.error('POST request failed:', url, error);
    throw error;
  }
}

// ---- Stage handlers ---------------------------------------------------
async function stage1() {
  setStatus(1, "Running…", "running");

  // Get the Confluence URL input
  const confluenceUrlEl = document.getElementById("confluence-url");
  const runIdEl = document.getElementById("run-id");

  if (!confluenceUrlEl || !runIdEl) {
    throw new Error("Required form elements not found. Please refresh the page.");
  }

  // Get input value from text field
  const inputSource = confluenceUrlEl.value.trim();

  console.log("Stage 1 input:", { inputSource });

  if (!inputSource) {
    setStatus(1, "Pending", "pending");
    showNotification("Please enter a Confluence URL or file path.", "error");
    return;
  }

  const payload = {
    run_id: state.run_id,
    source: inputSource,
  };

  console.log("Sending to /api/stage1:", payload);
  const res = await post("/api/stage1", payload);

  state.run_id = res.run_id;
  runIdEl.textContent = res.run_id;
  const b = res.brief;

  // Show skill automation badge
  const skillBadge = res.skill_automation ?
    '<span class="chip chip-ok" title="Automated by /sdlc-ingest skill"><i class="fas fa-magic"></i> Skill Automation</span>' : '';

  // Build skill stats if available
  let skillStats = '';
  if (res.skill_automation) {
    skillStats = `
      <div style="background: rgba(91, 157, 255, 0.1); border-left: 3px solid var(--accent); padding: 12px; margin: 12px 0; border-radius: 6px;">
        <strong><i class="fas fa-robot"></i> Skill Analysis:</strong>
        <ul style="margin: 8px 0 0 20px; font-size: 13px;">
          <li>User Stories Extracted: <strong>${res.stories_found || 0}</strong></li>
          <li>Acceptance Criteria Found: <strong>${res.acceptance_criteria_found || 0}</strong></li>
          <li>Open Questions: <strong>${res.open_questions ? res.open_questions.length : 0}</strong></li>
        </ul>
      </div>
    `;
  }

  show(1, `
    <p>${fileLink(res.artifact)} ${skillBadge}</p>
    ${skillStats}
    <table>
      <tr><th>Source</th><td><code>${escapeHtml(inputSource)}</code></td></tr>
      <tr><th>Title</th><td>${b.title}</td></tr>
      <tr><th>Business goal</th><td>${b.business_goal}</td></tr>
      <tr><th>Personas (${b.personas.length})</th><td>${b.personas.map(p=>`<span class="chip">${p.name}</span>`).join("")}</td></tr>
      <tr><th>Functional needs (${b.functional_needs.length})</th><td><ul>${b.functional_needs.map(x=>`<li>${x}</li>`).join("")}</ul></td></tr>
      <tr><th>Non-functional (${b.non_functional_constraints.length})</th><td><ul>${b.non_functional_constraints.map(x=>`<li>${x}</li>`).join("")}</ul></td></tr>
      <tr><th>Out of scope</th><td>${b.out_of_scope.map(x=>`<span class="chip">${x}</span>`).join("") || "—"}</td></tr>
      <tr><th>Open questions</th><td>${b.open_questions.length ? '<ul>' + b.open_questions.map(q=>`<li>${q}</li>`).join("") + '</ul>' : "<em>none</em>"}</td></tr>
    </table>`);
  setStatus(1, "Complete", "done");
  unlock(2);

  // Disable Stage 1 button after requirements are ingested
  disableButton('stage1');
}

async function stage2() {
  setStatus(2, "Running…", "running");
  const res = await post("/api/stage2", { run_id: state.run_id });

  // Map story ID -> Jira issue key for the table
  const jiraMap = {};
  (res.jira_issues || []).forEach(j => { jiraMap[j.story_id] = j; });

  const rows = res.backlog.stories.map(s => {
    const jira = jiraMap[s.id];
    let jiraCell = "—";
    if (jira) {
      if (jira.url) {
        jiraCell = `<a href="${jira.url}" target="_blank" rel="noopener" class="jira-link">
          <i class="fab fa-jira"></i> ${jira.issue_key}
        </a>`;
      } else {
        jiraCell = `<span class="chip">${jira.issue_key}</span>`;
      }
    }
    return `
    <tr>
      <td><strong>${s.id}</strong></td>
      <td>${jiraCell}</td>
      <td>${s.as_a_statement || `As a ${s.persona}, I want ${s.want}, so that ${s.so_that}.`}</td>
      <td>${s.acceptance_criteria.length}</td>
      <td>${(s.dependencies||[]).map(d=>`<span class="chip">${d}</span>`).join("") || "—"}</td>
    </tr>`;
  }).join("");

  // Strict LLM detection: only "llm" means Claude was actually used
  const isLLM = res.generation_source === "llm";
  const badgeLabel = isLLM
    ? `<i class="fas fa-brain"></i> LLM (Claude)`
    : `<i class="fas fa-cog"></i> Rules-based`;
  const badge = `<span class="chip ${isLLM ? "chip-ok" : "chip-warn"}" title="${res.generation_backend || ""}">
      ${badgeLabel}
    </span>`;

  // LLM detail box (shows the actual generation path)
  const detailBlock = res.generation_detail
    ? `<p class="generation-detail ${isLLM ? 'is-llm' : 'is-rules'}">
         <i class="fas fa-${isLLM ? 'check-circle' : 'info-circle'}"></i>
         <strong>${isLLM ? 'LLM Used' : 'LLM Not Used'}:</strong>
         ${res.generation_detail}
         <span class="backend-info">(backend: <code>${res.generation_backend}</code>)</span>
       </p>`
    : "";

  // Jira mode badge
  const isRealJira = res.jira_mode === "JiraClient";
  const jiraBadge = `<span class="chip ${isRealJira ? "chip-ok" : "chip-warn"}" title="${res.jira_url || ''}">
      <i class="fab fa-jira"></i> ${isRealJira ? `Real Jira (${res.jira_project_key})` : "Mock Jira"}
    </span>`;
  const jiraSummary = res.jira_issues && res.jira_issues.length
    ? `<p>Created <strong>${res.jira_issues.length}</strong> Jira issue(s) in project <code>${res.jira_project_key}</code></p>`
    : "";

  show(2, `
    <p>${fileLink(res.artifact)} ${badge} ${jiraBadge}</p>
    ${detailBlock}
    ${jiraSummary}
    <table><tr><th>ID</th><th>Jira</th><th>Story</th><th>ACs</th><th>Dependencies</th></tr>${rows}</table>`);
  setStatus(2, "Awaiting PO", "running");
  document.getElementById("po-gate").hidden = false;

  // Disable Stage 2 button after stories are generated
  disableButton('stage2');
}

async function approve() {
  // Validation
  if (!state.run_id) {
    throw new Error('No active run. Please complete Stage 1 and 2 first.');
  }

  const approver = document.getElementById("approver").value;
  if (!approver || !approver.trim()) {
    throw new Error('Approver name is required.');
  }

  console.log('Approving backlog:', { run_id: state.run_id, approver });

  const result = await post("/api/approve", { run_id: state.run_id, approver });

  console.log('Approval successful:', result);

  document.getElementById("po-gate").hidden = true;
  setStatus(2, "Approved", "done");
  unlock(3);
  updateProgressBar();

  // If autonomous mode is active, resume Phase 2 automatically
  const approveBtn = document.querySelector('button[data-action="approve"]');
  if (approveBtn && approveBtn.dataset.autonomousMode === "true") {
    delete approveBtn.dataset.autonomousMode;
    showNotification("✅ PO approved. Resuming autonomous pipeline...", "success");
    await resumeAutonomous();
  }
}

async function stage3() {
  setStatus(3, "Running…", "running");
  const inject_defect = document.getElementById("inject-defect").checked;
  const res = await post("/api/stage3", { run_id: state.run_id, inject_defect });
  const isLLM = res.generation_source === "llm" || res.generation_source === "skill_automation";
  const badge = `<span class="chip ${isLLM ? "chip-ok" : "chip-warn"}" title="${res.generation_backend || ""}">
      ${isLLM ? "LLM" : "Rules"}: ${res.generation_backend || "stub"}
    </span>`;

  const filesWritten = res.files_written || [];
  const prFiles = (res.pr && res.pr.files) || [];

  const filesBlock = filesWritten.length > 0
    ? `<p>Files written: ${filesWritten.map(fileLink).join(" ")}</p>`
    : `<p><em>⚠️ No files generated — backlog had no user stories. Check that Stage 1 ingested real requirements.</em></p>`;

  // Build tabbed file preview - one tab per file
  let previewBlock = "";
  if (prFiles.length > 0) {
    const tabs = prFiles.map((f, i) => {
      const label = f.path.replace(/^.*\//, "");  // just the filename
      const dir = f.path.startsWith("tests/") ? "test" : "src";
      return `<button class="code-tab ${i === 0 ? 'active' : ''}"
                      data-tab-idx="${i}" data-stage="3"
                      title="${f.path}">
                <i class="fas fa-${dir === 'test' ? 'vial' : 'file-code'}"></i> ${label}
              </button>`;
    }).join("");

    const panes = prFiles.map((f, i) => `
      <div class="code-pane ${i === 0 ? 'active' : ''}" data-pane-idx="${i}" data-stage="3">
        <div class="code-pane-header">
          <code class="file-path">${f.path}</code>
          <span class="code-meta">
            <span class="chip">${f.language}</span>
            <span class="chip">${f.contents.split("\n").length} lines</span>
            <button class="copy-btn" data-copy-target="${i}-3" title="Copy to clipboard">
              <i class="fas fa-copy"></i> Copy
            </button>
          </span>
        </div>
        <pre id="code-${i}-3" class="code-block">${escapeHtml(f.contents)}</pre>
      </div>`).join("");

    previewBlock = `
      <details open class="code-viewer">
        <summary><strong>Preview generated code</strong> (${prFiles.length} files)</summary>
        <div class="code-tabs">${tabs}</div>
        <div class="code-panes">${panes}</div>
      </details>`;
  }

  show(3, `
    <p><strong>Draft PR #${res.pr.number}</strong> on <code>${res.pr.branch}</code> · state: <span class="chip">${res.pr.state}</span> ${badge}</p>
    ${filesBlock}
    ${previewBlock}`);

  // Wire up tab switching
  document.querySelectorAll('.code-tab[data-stage="3"]').forEach(tab => {
    tab.addEventListener('click', () => {
      const idx = tab.dataset.tabIdx;
      document.querySelectorAll('.code-tab[data-stage="3"]').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.code-pane[data-stage="3"]').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const pane = document.querySelector(`.code-pane[data-stage="3"][data-pane-idx="${idx}"]`);
      if (pane) pane.classList.add('active');
    });
  });

  // Wire up copy buttons
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const target = document.getElementById(`code-${btn.dataset.copyTarget}`);
      if (target) {
        try {
          await navigator.clipboard.writeText(target.textContent);
          const orig = btn.innerHTML;
          btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
          setTimeout(() => { btn.innerHTML = orig; }, 1500);
        } catch (e) { console.warn("Copy failed:", e); }
      }
    });
  });

  setStatus(3, "Complete", "done");
  unlock(4);

  // Disable Stage 3 button after code generation
  disableButton('stage3');
}

async function stage4() {
  setStatus(4, "Running…", "running");
  const res = await post("/api/stage4", { run_id: state.run_id });
  const r = res.report;
  const rows = r.findings.map(f => `
    <tr>
      <td><span class="chip ${f.severity}">${f.severity}</span></td>
      <td>${f.category}</td>
      <td><code>${f.file}</code>${f.line ? ":"+f.line : ""}</td>
      <td>${f.message}</td>
    </tr>`).join("") || `<tr><td colspan="4"><em>no findings</em></td></tr>`;
  const verdictCls = r.verdict === "pass" ? "verdict-go" : "verdict-nogo";
  const isLLM = (res.review_source || "").startsWith("llm");
  const badge = `<span class="chip ${isLLM ? "chip-ok" : "chip-warn"}" title="${res.review_backend || ""}">
      ${isLLM ? "LLM" : "Rules"}: ${res.review_backend || "stub"}
    </span>`;
  // Render Jira transitions if any
  const s4Transitions = res.jira_transitions || [];
  const s4TransitionsHtml = s4Transitions.length > 0
    ? `<details open><summary>🎫 Jira Cards Updated to "Ready for QA" (${s4Transitions.filter(t=>t.transitioned).length}/${s4Transitions.length})</summary>
        <ul>${s4Transitions.map(t => `<li><strong>${t.issue_key}</strong> (${t.story_id}): ${t.transitioned ? '<span class="chip chip-ok">✓ Ready for QA</span>' : '<span class="chip chip-warn">✗ Failed</span>'}</li>`).join('')}</ul>
       </details>`
    : '';

  show(4, `
    <p><span class="${verdictCls}">Verdict: ${r.verdict.toUpperCase()}</span> ${badge}</p>
    <p>Stored: ${res.stored.map(fileLink).join(" ")}</p>
    ${s4TransitionsHtml}
    <table><tr><th>Severity</th><th>Category</th><th>Location</th><th>Message</th></tr>${rows}</table>`);
  setStatus(4, r.verdict === "pass" ? "Pass" : "Fail", r.verdict === "pass" ? "done" : "fail");
  if (r.verdict === "pass") {
    unlock(5);
    // Disable Stage 4 button after successful review
    disableButton('stage4');
  } else {
    alert("Stage 4 failed — re-run Stage 3 without the seeded defect, then re-run Stage 4.");
  }
}

async function stage5() {
  setStatus(5, "Running tests…", "running");
  const res = await post("/api/stage5", { run_id: state.run_id });
  const pw = res.playwright_result || {};
  let pwBlock;
  if (pw.executed) {
    pwBlock = `<p>Playwright (TS): exit code <strong>${pw.exit_code}</strong> · ${fileLink(pw.log_path)} · report dir: <code>${pw.report_dir}</code></p>
      <details><summary>Playwright output tail</summary><pre>${escapeHtml(pw.tail || "")}</pre></details>`;
  } else {
    pwBlock = `<p><em>Playwright not executed (${pw.reason || "unknown"}). Files generated under ${fileLink(res.playwright_dir)} — run <code>npx playwright install &amp;&amp; npx playwright test</code> there.</em></p>`;
  }

  show(5, `
    <p><strong>Manual test cases (Excel):</strong> ${fileLink(res.manual_tests_xlsx)}</p>
    <p><strong>Pytest automation:</strong> ${fileLink(res.automation_dir)} — exit code <strong>${res.pytest_exit_code}</strong></p>
    <p><strong>Playwright (TS) suite:</strong> ${fileLink(res.playwright_dir)} · ${res.playwright_specs.length} spec file(s)</p>
    ${pwBlock}
    <p>Coverage map: ${res.suite.coverage_map.length} ACs mapped to ${res.suite.files.length} pytest files.</p>
    <details><summary>pytest tail</summary><pre>${escapeHtml(res.pytest_tail)}</pre></details>`);
  setStatus(5, res.pytest_exit_code === 0 ? "Green" : "Red", res.pytest_exit_code === 0 ? "done" : "fail");
  unlock(6);
}

// ---- Stage 5: New 4-button workflow -----------------------------------
async function stage5Manual() {
  if (!state.run_id) {
    throw new Error('No active run. Please complete earlier stages first.');
  }

  const res = await post("/api/stage5/manual-tests", { run_id: state.run_id });

  show('manual', `
    <p><strong>✓ Manual Test Cases Generated</strong></p>
    <p>📄 Excel: ${fileLink(res.excel_file || 'N/A')}</p>
    <p>📄 JSON: ${fileLink(res.output_file || 'N/A')}</p>
    <p>📊 Test Cases: ${res.total_test_cases || 0}</p>
    <p class="success">Manual test cases generated successfully!</p>
  `);

  state.stage5.manualTestsGenerated = true;
  disableButton('stage5-manual');
  enableButton('stage5-automation');
  showNotification('Manual test cases generated successfully!', 'success');
}

async function stage5Automation() {
  if (!state.stage5.manualTestsGenerated) {
    throw new Error('Generate manual tests first');
  }

  const res = await post("/api/stage5/automation-scripts", { run_id: state.run_id });

  show('automation', `
    <p><strong>✓ Automation Scripts Generated</strong></p>
    <p>🤖 Scripts: ${res.total_scripts || 0}</p>
    <p>📁 Directory: ${fileLink(res.output_dir || 'N/A')}</p>
    <p>📄 Metadata: ${fileLink(res.metadata_file || 'N/A')}</p>
    <p class="success">Automation scripts generated successfully!</p>
  `);

  state.stage5.automationScriptsGenerated = true;
  disableButton('stage5-automation');
  enableButton('stage5-execute');
  showNotification('Automation scripts generated!', 'success');
}

async function stage5Execute() {
  if (!state.stage5.automationScriptsGenerated) {
    throw new Error('Generate automation scripts first');
  }

  const res = await post("/api/stage5/execute-tests", { run_id: state.run_id });

  const failed = res.failed || 0;
  const passed = res.passed || 0;
  const total = res.total_tests || res.total || 0;  // Use total_tests from API
  const hasFailures = failed > 0;
  const statusCls = hasFailures ? 'fail' : 'done';
  const statusIcon = hasFailures ? '⚠️' : '✓';

  show('execute', `
    <p><strong>${statusIcon} Tests Executed</strong></p>
    <p>Total: ${total} | <span class="chip chip-ok">Passed: ${passed}</span> | <span class="chip chip-warn">Failed: ${failed}</span></p>
    <p>Pass Rate: ${res.pass_rate || 0}%</p>
    <p>Results: ${res.output_file ? fileLink(res.output_file) : 'N/A'}</p>
    <p>Report: ${res.html_report ? fileLink(res.html_report) : 'N/A'}</p>
    <p class="${statusCls}">Tests executed successfully</p>
  `);

  state.stage5.testsExecuted = true;
  state.stage5.hasFailures = hasFailures;
  disableButton('stage5-execute');

  if (hasFailures) {
    enableButton('stage5-heal');
    showNotification(`${failed} tests failed - healing available`, 'error');
  } else {
    showNotification('All tests passed!', 'success');
    setStatus(5, 'Complete', 'done');
    unlock(6);
  }
}

async function stage5Heal() {
  if (!state.stage5.hasFailures) {
    throw new Error('No failures to heal');
  }

  const res = await post("/api/stage5/heal-tests", { run_id: state.run_id });

  const fixesApplied = res.fixes_applied || 0;
  const suggestions = res.healing_suggestions || [];

  const suggestionsHtml = suggestions.length > 0
    ? suggestions.map(s => `
        <div class="healing-suggestion">
          <strong>🔧 ${s.test_id || 'Unknown test'}</strong>
          <p>Category: ${s.failure_category || 'Unknown'}</p>
          <p>Root Cause: ${s.root_cause || 'No analysis'}</p>
          <p>Confidence: ${s.confidence_score || 0}%</p>
          ${s.fix_applied ? '<span class="chip chip-ok">✓ Fix Applied</span>' : '<span class="chip chip-warn">Manual Review Needed</span>'}
        </div>
      `).join('')
    : '<p class="text-muted">No specific suggestions generated</p>';

  show('heal', `
    <p><strong>✨ Test Healing Complete</strong></p>
    <p>Failures Analyzed: ${res.failures_analyzed || 0}</p>
    <p>Auto-Fixable: ${res.auto_fixable || 0}</p>
    <p>Fixes Applied: <strong>${fixesApplied}</strong></p>
    <p>Manual Review Needed: ${res.manual_review_needed || 0}</p>
    <p>Report: ${res.output_file ? fileLink(res.output_file) : 'N/A'}</p>
    <details ${suggestions.length > 0 ? 'open' : ''}><summary>Healing Details</summary>${suggestionsHtml}</details>
    ${fixesApplied > 0 ? '<p class="info">💡 Fixes have been applied. Re-run tests to verify.</p>' : ''}
  `);

  disableButton('stage5-heal');

  if (fixesApplied > 0) {
    showNotification(`${fixesApplied} fixes applied - re-run tests to verify`, 'success');
    // Re-enable execute button so user can re-run tests
    enableButton('stage5-execute');
  } else {
    showNotification('No auto-fixes available - manual review required', 'warning');
    setStatus(5, 'Manual Review Required', 'warn');
    unlock(6);
  }
}

// Helper functions for Stage 5 workflow
function enableButton(action) {
  const btn = document.querySelector(`button[data-action="${action}"]`);
  if (btn) {
    btn.disabled = false;
    delete btn.dataset.completed;  // Clear completed flag so button can be clicked again
  }
}

function disableButton(action) {
  const btn = document.querySelector(`button[data-action="${action}"]`);
  if (btn) {
    btn.disabled = true;
    btn.dataset.completed = "true";  // Mark as completed so finally block won't re-enable
  }
}

async function stage6() {
  setStatus(6, "Running…", "running");
  const res = await post("/api/stage6", { run_id: state.run_id });
  const d = res.decision;
  const gates = Object.entries(d.gates).map(([k,v]) =>
    `<span class="chip ${v?"low":"high"}">${v?"✓":"✗"} ${k}</span>`).join(" ");
  const cls = d.go ? "verdict-go" : "verdict-nogo";
  // Render Jira transitions if any
  const transitions = res.jira_transitions || [];
  const transitionsHtml = transitions.length > 0
    ? `<details open><summary>🎫 Jira Cards Updated to Done (${transitions.filter(t=>t.transitioned).length}/${transitions.length})</summary>
        <ul>${transitions.map(t => `<li><strong>${t.issue_key}</strong> (${t.story_id}): ${t.transitioned ? '<span class="chip chip-ok">✓ Done</span>' : '<span class="chip chip-warn">✗ Failed</span>'}</li>`).join('')}</ul>
       </details>`
    : '';

  show(6, `
    <p><span class="${cls}">${d.go ? "GO — ready to deploy" : "NO-GO"}</span></p>
    <p>${gates}</p>
    ${d.blocking_reasons.length ? `<ul>${d.blocking_reasons.map(r=>`<li>${r}</li>`).join("")}</ul>` : ""}
    ${transitionsHtml}
    <details open><summary>Draft release note</summary><pre>${escapeHtml(d.release_note)}</pre></details>`);
  setStatus(6, d.go ? "GO" : "NO-GO", d.go ? "done" : "fail");

  // Disable Stage 6 button after deployment check
  disableButton('stage6');
}

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

// ---- Wire buttons -----------------------------------------------------
const handlers = {
  stage1, stage2, approve, stage3, stage4, stage5, stage6,
  'stage5-manual': stage5Manual,
  'stage5-automation': stage5Automation,
  'stage5-execute': stage5Execute,
  'stage5-heal': stage5Heal,
  autonomous: autonomous
};

function initializeApp() {
  console.log('Initializing SDLC Agent UI...');

  document.querySelectorAll("button[data-action]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const action = btn.dataset.action;
      const originalText = btn.textContent;
      btn.disabled = true;

      // Add loading spinner
      if (!action.includes('approve')) {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + originalText;
      }

      try {
        await handlers[action]();
        // Success animation
        if (action.includes('stage')) {
          const stageNum = action.replace('stage', '');
          const card = document.getElementById(`stage${stageNum}`);
          if (card) {
            card.style.animation = 'none';
            setTimeout(() => {
              card.style.animation = 'fadeIn 0.5s ease-in';
            }, 10);
          }
        }
      }
      catch (e) {
        // Styled error notification with more details
        const errorMsg = e.message || e.toString();
        showNotification(`${action.toUpperCase()}: ${errorMsg}`, 'error');
        console.error('Action failed:', action, e);

        // Reset button state on error
        if (action.includes('stage')) {
          const stageNum = action.replace('stage', '');
          setStatus(stageNum, 'Error', 'fail');
        }
      }
      finally {
        // Only re-enable if button wasn't marked as completed by stage handler
        if (btn.dataset.completed !== "true") {
          btn.disabled = false;
        }
        btn.textContent = originalText;
      }
    });
  });

  console.log('✓ SDLC Agent UI initialized');
}

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  // DOM already loaded
  initializeApp();
}

// Custom notification system
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.innerHTML = `
    <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
    <span>${message}</span>
  `;
  notification.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    background: ${type === 'error' ? 'rgba(255, 107, 107, 0.95)' : 'rgba(91, 157, 255, 0.95)'};
    color: white;
    padding: 16px 20px;
    border-radius: 10px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    z-index: 1000;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
    font-weight: 600;
    animation: slideIn 0.3s ease-out;
    max-width: 400px;
  `;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-in';
    setTimeout(() => notification.remove(), 300);
  }, 5000);
}

// Add animations for notifications (safely)
function addNotificationStyles() {
  if (document.head && !document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    addNotificationStyles();
    updateProgressBar();
  });
} else {
  addNotificationStyles();
  updateProgressBar();
}
