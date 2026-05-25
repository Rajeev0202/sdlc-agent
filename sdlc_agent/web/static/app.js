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
  const progress = (state.completedStages / 6) * 100;
  const bar = document.getElementById('progress-bar');
  if (bar) {
    bar.style.width = `${progress}%`;
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

  // Null-safe element access
  const brdSelectEl = document.getElementById("brd-select");
  const brdTextEl = document.getElementById("brd-text");
  const runIdEl = document.getElementById("run-id");

  if (!brdSelectEl || !brdTextEl || !runIdEl) {
    throw new Error("Required form elements not found. Please refresh the page.");
  }

  const brd_filename = brdSelectEl.value || "";
  const brd_text = brdTextEl.value || "";

  console.log("Stage 1 inputs:", { brd_filename, brd_text: brd_text.substring(0, 50) + "..." });

  if (!brd_filename && !brd_text.trim()) {
    setStatus(1, "Pending", "pending");
    showNotification("Please pick a sample BRD or paste requirement text.", "error");
    return;
  }

  const res = await post("/api/stage1", {
    run_id: state.run_id, brd_filename, brd_text,
  });

  state.run_id = res.run_id;
  runIdEl.textContent = res.run_id;
  const b = res.brief;
  show(1, `
    <p>${fileLink(res.artifact)}</p>
    <table>
      <tr><th>Title</th><td>${b.title}</td></tr>
      <tr><th>Business goal</th><td>${b.business_goal}</td></tr>
      <tr><th>Personas (${b.personas.length})</th><td>${b.personas.map(p=>`<span class="chip">${p.name}</span>`).join("")}</td></tr>
      <tr><th>Functional needs (${b.functional_needs.length})</th><td><ul>${b.functional_needs.map(x=>`<li>${x}</li>`).join("")}</ul></td></tr>
      <tr><th>Non-functional (${b.non_functional_constraints.length})</th><td><ul>${b.non_functional_constraints.map(x=>`<li>${x}</li>`).join("")}</ul></td></tr>
      <tr><th>Out of scope</th><td>${b.out_of_scope.map(x=>`<span class="chip">${x}</span>`).join("") || "—"}</td></tr>
      <tr><th>Open questions</th><td>${b.open_questions.length ? b.open_questions.map(q=>`<li>${q}</li>`).join("") : "<em>none</em>"}</td></tr>
    </table>`);
  setStatus(1, "Complete", "done");
  unlock(2);
}

async function stage2() {
  setStatus(2, "Running…", "running");
  const res = await post("/api/stage2", { run_id: state.run_id });
  const rows = res.backlog.stories.map(s => `
    <tr>
      <td><strong>${s.id}</strong></td>
      <td>${s.as_a_statement || `As a ${s.persona}, I want ${s.want}, so that ${s.so_that}.`}</td>
      <td>${s.acceptance_criteria.length}</td>
      <td>${s.dependencies.map(d=>`<span class="chip">${d}</span>`).join("") || "—"}</td>
    </tr>`).join("");
  const isLLM = res.generation_source === "llm";
  const badge = `<span class="chip ${isLLM ? "chip-ok" : "chip-warn"}" title="${res.generation_backend || ""}">
      ${isLLM ? "LLM" : "Rules"}: ${res.generation_backend || "stub"}
    </span>`;
  show(2, `
    <p>${fileLink(res.artifact)} ${badge}</p>
    <table><tr><th>ID</th><th>Story</th><th>ACs</th><th>Dependencies</th></tr>${rows}</table>`);
  setStatus(2, "Awaiting PO", "running");
  document.getElementById("po-gate").hidden = false;
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
}

async function stage3() {
  setStatus(3, "Running…", "running");
  const inject_defect = document.getElementById("inject-defect").checked;
  const res = await post("/api/stage3", { run_id: state.run_id, inject_defect });
  const isLLM = res.generation_source === "llm";
  const badge = `<span class="chip ${isLLM ? "chip-ok" : "chip-warn"}" title="${res.generation_backend || ""}">
      ${isLLM ? "LLM" : "Rules"}: ${res.generation_backend || "stub"}
    </span>`;
  show(3, `
    <p><strong>Draft PR #${res.pr.number}</strong> on <code>${res.pr.branch}</code> · state: <span class="chip">${res.pr.state}</span> ${badge}</p>
    <p>Files written: ${res.files_written.map(fileLink).join(" ")}</p>
    <details><summary>Preview generated code</summary><pre>${escapeHtml(res.pr.files[0].contents)}</pre></details>`);
  setStatus(3, "Complete", "done");
  unlock(4);
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
  show(4, `
    <p><span class="${verdictCls}">Verdict: ${r.verdict.toUpperCase()}</span> ${badge}</p>
    <p>Stored: ${res.stored.map(fileLink).join(" ")}</p>
    <table><tr><th>Severity</th><th>Category</th><th>Location</th><th>Message</th></tr>${rows}</table>`);
  setStatus(4, r.verdict === "pass" ? "Pass" : "Fail", r.verdict === "pass" ? "done" : "fail");
  if (r.verdict === "pass") unlock(5);
  else alert("Stage 4 failed — re-run Stage 3 without the seeded defect, then re-run Stage 4.");
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
    <p>📄 File: ${fileLink(res.file_path)}</p>
    <p>📊 Stories: ${res.story_count} | Test Cases: ${res.test_case_count}</p>
    <p class="success">${res.message}</p>
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
    <p>🤖 Scripts: ${res.script_count}</p>
    <p>📁 Directory: ${fileLink(res.playwright_dir)}</p>
    <details><summary>View generated scripts</summary>
      <ul>${res.scripts.map(s => `<li>${fileLink(s)}</li>`).join('')}</ul>
    </details>
    <p class="success">${res.message}</p>
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

  const statusCls = res.failed > 0 ? 'fail' : 'done';
  const statusIcon = res.failed > 0 ? '⚠️' : '✓';

  show('execute', `
    <p><strong>${statusIcon} Tests Executed</strong></p>
    <p>Total: ${res.total} | <span class="chip chip-ok">Passed: ${res.passed}</span> | <span class="chip chip-warn">Failed: ${res.failed}</span></p>
    <p>Exit Code: <code>${res.exit_code}</code></p>
    <p>Results: ${fileLink(res.result_file)}</p>
    <p>Log: ${fileLink(res.log_file)}</p>
    <p class="${statusCls}">${res.message}</p>
  `);

  state.stage5.testsExecuted = true;
  state.stage5.hasFailures = res.has_failures;
  disableButton('stage5-execute');

  if (res.has_failures) {
    enableButton('stage5-heal');
    showNotification(`${res.failed} tests failed - healing available`, 'error');
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

  const suggestionsHtml = res.suggestions.map(s => `
    <div class="healing-suggestion">
      <strong>🔧 ${s.test}</strong>
      <p>Issue: ${s.issue}</p>
      <p class="suggestion">💡 ${s.suggestion}</p>
    </div>
  `).join('');

  show('heal', `
    <p><strong>✨ Test Healing Analysis Complete</strong></p>
    <p>Failures Analyzed: ${res.failures_found}</p>
    <p>Report: ${fileLink(res.healing_report)}</p>
    <details open><summary>Top Healing Suggestions</summary>${suggestionsHtml}</details>
    <p class="success">${res.message}</p>
  `);

  disableButton('stage5-heal');
  showNotification('Test healing suggestions generated!', 'success');
  setStatus(5, 'Healed', 'done');
  unlock(6);
}

// Helper functions for Stage 5 workflow
function enableButton(action) {
  const btn = document.querySelector(`button[data-action="${action}"]`);
  if (btn) {
    btn.disabled = false;
  }
}

function disableButton(action) {
  const btn = document.querySelector(`button[data-action="${action}"]`);
  if (btn) {
    btn.disabled = true;
  }
}

async function stage6() {
  setStatus(6, "Running…", "running");
  const res = await post("/api/stage6", { run_id: state.run_id });
  const d = res.decision;
  const gates = Object.entries(d.gates).map(([k,v]) =>
    `<span class="chip ${v?"low":"high"}">${v?"✓":"✗"} ${k}</span>`).join(" ");
  const cls = d.go ? "verdict-go" : "verdict-nogo";
  show(6, `
    <p><span class="${cls}">${d.go ? "GO — ready to deploy" : "NO-GO"}</span></p>
    <p>${gates}</p>
    ${d.blocking_reasons.length ? `<ul>${d.blocking_reasons.map(r=>`<li>${r}</li>`).join("")}</ul>` : ""}
    <details open><summary>Draft release note</summary><pre>${escapeHtml(d.release_note)}</pre></details>`);
  setStatus(6, d.go ? "GO" : "NO-GO", d.go ? "done" : "fail");
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

// ---- Wire buttons -----------------------------------------------------
const handlers = {
  stage1, stage2, approve, stage3, stage4, stage5, stage6,
  'stage5-manual': stage5Manual,
  'stage5-automation': stage5Automation,
  'stage5-execute': stage5Execute,
  'stage5-heal': stage5Heal
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
        btn.disabled = false;
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
