// SDLC Agent · Stage handlers (Stages 1-6 + Stage 5 test workflow)
// Classic (non-module) script — globals shared across files; load order matters.

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
