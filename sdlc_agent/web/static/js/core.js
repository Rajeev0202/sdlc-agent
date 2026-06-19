// SDLC Agent · Core: state, progress, status, locking, fetch helper
// Classic (non-module) script — globals shared across files; load order matters.
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
