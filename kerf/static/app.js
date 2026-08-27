const state = { health: null, cases: [], runs: [], selected: new Set() };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const formatMoney = (value, digits = 4) => `$${Number(value || 0).toFixed(digits)}`;
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

function renderMetrics(metrics) {
  const items = [
    ["Evaluation cases created", metrics.evaluation_cases_created],
    ["Model versions compared", metrics.model_versions_compared],
    ["Runs completed", metrics.runs_completed],
    ["Incorrect outputs detected", metrics.incorrect_outputs_detected],
    ["Average latency", `${Number(metrics.average_latency_ms || 0).toFixed(1)} ms`],
    ["Total estimated cost", formatMoney(metrics.total_cost_usd, 6)],
    ["Beta users", metrics.beta_users],
    ["Releases / Git commits", `${metrics.product_releases} / ${metrics.git_commits}`],
  ];
  $("#metricsGrid").innerHTML = items.map(([label, value], index) =>
    `<article class="metric"><span>${label}</span><b class="${index < 4 ? 'acid' : ''}">${escapeHtml(value)}</b></article>`
  ).join("");
}

function renderCases(filter = "all") {
  const visible = state.cases.filter(item => filter === "all" || item.category === filter);
  $("#caseGrid").innerHTML = visible.map(item => `
    <article class="case-card">
      <div class="case-meta"><span>${escapeHtml(item.id)}</span><span>${escapeHtml(item.difficulty)}</span></div>
      <h3>${escapeHtml(item.title)}</h3>
      <p>${escapeHtml(item.question)}</p>
      <div class="case-answer">EXPECTED / ${escapeHtml(item.expected_answer)}</div>
    </article>`).join("");
}

function runDetail(run) {
  const fixture = run.provider === "fixture";
  $("#latestRun").classList.remove("empty-state");
  $("#latestRun").innerHTML = `
    <div class="run-top">
      <div><div class="panel-kicker">RUN ${run.id} / ${fixture ? 'FIXTURE' : 'LIVE MODEL'}</div><h3>${escapeHtml(run.model)}</h3><p>${escapeHtml(run.created_at)}</p></div>
      <div class="score-ring">${Number(run.average_score).toFixed(0)}</div>
    </div>
    <div class="run-stats">
      <div class="run-stat"><span>Passed</span><b>${run.passed_count}/${run.case_count}</b></div>
      <div class="run-stat"><span>Latency</span><b>${Number(run.average_latency_ms).toFixed(1)} ms</b></div>
      <div class="run-stat"><span>Tokens</span><b>${run.input_tokens + run.output_tokens}</b></div>
      <div class="run-stat"><span>Cost</span><b>${formatMoney(run.estimated_cost_usd, 6)}</b></div>
    </div>
    <div class="notice" style="border-color:${fixture ? 'var(--warning)' : 'var(--good)'}">${fixture ? 'Deterministic fixture: the evaluation product ran, but no external model was called.' : 'Live API run: token, latency, cost, and failure evidence were recorded.'}</div>
    <div class="report-links">
      <a class="button ghost small" href="/api/reports/${run.id}.md">Markdown report</a>
      <a class="button ghost small" href="/api/reports/${run.id}.csv">CSV results</a>
      <a class="button ghost small" href="/api/reports/${run.id}.json">JSON evidence</a>
    </div>
    <div class="result-list">${(run.results || []).map(result => `
      <div class="result-row"><span>${escapeHtml(result.case_id)}</span><b>${Number(result.score).toFixed(0)}</b><span class="${result.passed ? 'pass' : 'fail'}">${result.passed ? 'PASS' : 'FAIL'}</span></div>`).join("")}</div>`;
}

function renderRuns() {
  const body = $("#runsBody");
  if (!state.runs.length) {
    body.innerHTML = '<tr><td colspan="8" class="table-empty">No completed runs yet.</td></tr>';
    return;
  }
  body.innerHTML = state.runs.map(run => `
    <tr data-run-id="${run.id}">
      <td><input class="run-check" type="checkbox" data-select-id="${run.id}" aria-label="Select run ${run.id}"></td>
      <td>#${run.id}</td><td>${escapeHtml(run.provider)} / ${escapeHtml(run.model)}</td>
      <td>${Number(run.average_score).toFixed(1)}</td><td>${run.passed_count}/${run.case_count}</td>
      <td>${Number(run.average_latency_ms).toFixed(1)} ms</td><td>${formatMoney(run.estimated_cost_usd, 6)}</td>
      <td>${new Date(run.created_at).toLocaleString()}</td>
    </tr>`).join("");
  $$('tr[data-run-id]').forEach(row => row.addEventListener('click', async event => {
    if (event.target.matches('input')) return;
    const run = await api(`/api/runs/${row.dataset.runId}`); runDetail(run);
    $("#lab").scrollIntoView({ behavior: "smooth" });
  }));
  $$('.run-check').forEach(box => box.addEventListener('change', () => {
    const id = Number(box.dataset.selectId);
    box.checked ? state.selected.add(id) : state.selected.delete(id);
    $("#compareButton").disabled = state.selected.size < 2 || state.selected.size > 5;
  }));
}

async function refresh() {
  const [health, tracker, cases, runs] = await Promise.all([
    api('/api/health'), api('/api/tracker'), api('/api/cases'), api('/api/runs')
  ]);
  state.health = health; state.cases = cases; state.runs = runs;
  $("#healthDot").style.background = "var(--good)";
  $("#healthText").textContent = health.openai_configured ? "API ready" : "Fixture ready";
  renderMetrics(tracker); renderCases(); renderRuns();
}

$("#provider").addEventListener("change", event => {
  const live = event.target.value === "openai";
  $("#model").value = live ? "gpt-5.6-luna" : "kerf-fixture-v1";
  $("#liveNotice").textContent = live
    ? (state.health?.openai_configured ? "A live API key is configured. This run may incur model charges." : "No API key is configured in the server environment. The request will be blocked safely.")
    : "Fixture runs prove the evaluation system—not model quality. No API charge is created.";
});

$("#runButton").addEventListener("click", async () => {
  const button = $("#runButton"); const progress = $("#runProgress");
  button.disabled = true; progress.hidden = false;
  try {
    const run = await api('/api/runs', { method: 'POST', body: JSON.stringify({ provider: $("#provider").value, model: $("#model").value }) });
    runDetail(run); await refresh();
  } catch (error) { alert(error.message); }
  finally { button.disabled = false; progress.hidden = true; }
});

$$('.filter').forEach(button => button.addEventListener('click', () => {
  $$('.filter').forEach(item => item.classList.remove('active')); button.classList.add('active'); renderCases(button.dataset.filter);
}));

$("#compareButton").addEventListener("click", async () => {
  try {
    const comparison = await api(`/api/compare?run_ids=${[...state.selected].join(',')}`);
    $("#comparison").hidden = false;
    $("#comparison").innerHTML = `<h3>Model comparison</h3><div class="comparison-grid">${comparison.run_summaries.map(run => `
      <div class="compare-card"><span>RUN ${run.id} / ${escapeHtml(run.model)}</span><b>${Number(run.average_score).toFixed(1)}</b><span>${run.passed_count}/${run.case_count} passed · ${Number(run.average_latency_ms).toFixed(1)} ms · ${formatMoney(run.estimated_cost_usd, 6)}</span></div>`).join('')}</div>`;
  } catch (error) { alert(error.message); }
});

$("#feedbackForm").addEventListener("submit", async event => {
  event.preventDefault(); const status = $("#feedbackStatus"); status.textContent = "Recording…";
  try {
    await api('/api/feedback', { method:'POST', body: JSON.stringify({ tester_alias: $("#testerAlias").value, role: $("#testerRole").value, rating: Number($("#rating").value), feedback: $("#feedback").value, consent_to_quote: $("#consent").checked }) });
    status.textContent = "Feedback recorded."; event.target.reset(); await refresh();
  } catch (error) { status.textContent = error.message; }
});

refresh().catch(error => {
  $("#healthDot").style.background = "var(--danger)"; $("#healthText").textContent = "Offline"; console.error(error);
});

