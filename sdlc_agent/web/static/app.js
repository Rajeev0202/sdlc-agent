// SDLC Agent — UI driver. Each stage button posts JSON to /api/stageN and
// renders the response into its card.

const state = { run_id: null };

function setStatus(stage, label, cls) {
  const el = document.getElementById(`s${stage}-status`);
  el.textContent = label;
  el.className = `status ${cls}`;
}
function unlock(stage) {
  const card = document.getElementById(`stage${stage}`);
  card.classList.remove("locked");
  card.querySelectorAll("button[data-action]").forEach(b => b.disabled = false);
  setStatus(stage, "Ready", "pending");
}
function fileLink(path) {
  return `<a class="file-link" href="/files/${path.replaceAll('\\\\', '/')}" target="_blank">${path}</a>`;
}
function show(stage, html) {
  document.getElementById(`s${stage}-out`).innerHTML = html;
}
async function post(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)
  });
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}

// ---- Stage handlers ---------------------------------------------------
async function stage1() {
  setStatus(1, "Running…", "running");
  const brd_filename = document.getElementById("brd-select").value;
  const brd_text = document.getElementById("brd-text").value;
  if (!brd_filename && !brd_text.trim()) {
    setStatus(1, "Pending", "pending");
    return alert("Pick a sample BRD or paste requirement text.");
  }
  const res = await post("/api/stage1", {
    run_id: state.run_id, brd_filename, brd_text,
  });
  state.run_id = res.run_id;
  document.getElementById("run-id").textContent = res.run_id;
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
  const approver = document.getElementById("approver").value;
  await post("/api/approve", { run_id: state.run_id, approver });
  document.getElementById("po-gate").hidden = true;
  setStatus(2, "Approved", "done");
  unlock(3);
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
const handlers = { stage1, stage2, approve, stage3, stage4, stage5, stage6 };
document.querySelectorAll("button[data-action]").forEach(btn => {
  btn.addEventListener("click", async () => {
    const action = btn.dataset.action;
    btn.disabled = true;
    try { await handlers[action](); }
    catch (e) { alert(`Error in ${action}: ${e.message}`); console.error(e); }
    finally { btn.disabled = false; }
  });
});
