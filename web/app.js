"use strict";

const state = { scenarios: [], selected: null, filter: "all", search: "", latest: {}, history: loadHistory() };
const $ = (id) => document.getElementById(id);

function loadHistory() {
  try { return JSON.parse(localStorage.getItem("refund-eval-history") || "[]"); }
  catch { return []; }
}
function saveHistory() { localStorage.setItem("refund-eval-history", JSON.stringify(state.history.slice(0, 20))); }
function text(value) { return value === null || value === undefined ? "—" : String(value); }
function money(cents) { return cents === null || cents === undefined ? "No amount expected" : `$${(cents / 100).toFixed(2)} proposed`; }
function label(value) { return text(value).replaceAll("_", " "); }
function showToast(message) { const toast = $("toast"); toast.textContent = message; toast.classList.add("show"); clearTimeout(showToast.timer); showToast.timer = setTimeout(() => toast.classList.remove("show"), 2600); }

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const body = await response.json().catch(() => ({ error: { message: "Malformed API response" } }));
  if (!response.ok) throw new Error(body.error?.message || `Request failed (${response.status})`);
  return body;
}

function renderScenarios() {
  const list = $("scenario-list"); list.replaceChildren();
  const query = state.search.toLowerCase();
  const visible = state.scenarios.filter(s => (state.filter === "all" || s.category === state.filter) && (s.title.toLowerCase().includes(query) || s.message.toLowerCase().includes(query)));
  if (!visible.length) { const empty = document.createElement("div"); empty.className = "empty-history"; empty.textContent = "No matching scenarios."; list.append(empty); return; }
  visible.forEach((scenario, index) => {
    const button = document.createElement("button"); button.className = "scenario-item" + (state.selected?.id === scenario.id ? " active" : "");
    button.dataset.id = scenario.id; button.setAttribute("aria-pressed", state.selected?.id === scenario.id ? "true" : "false");
    const run = state.latest[scenario.id];
    button.innerHTML = `<span class="scenario-index">${String(index + 1).padStart(2, "0")}</span><span class="scenario-copy"><strong></strong><span></span></span><i class="latest-dot ${run?.status || ""}"></i>`;
    button.querySelector("strong").textContent = scenario.title; button.querySelector(".scenario-copy span").textContent = label(scenario.expected_outcome);
    button.addEventListener("click", () => selectScenario(scenario.id)); list.append(button);
  });
}

async function selectScenario(id) {
  try {
    const detail = await api(`/api/scenarios/${encodeURIComponent(id)}`); state.selected = detail; renderScenarios(); renderScenario(detail);
    closeSidebar();
    const previous = state.latest[id]; if (previous) renderRun(previous); else clearRun();
  } catch (error) { showToast(error.message); }
}

function renderScenario(s) {
  $("scenario-id").textContent = s.id; $("scenario-title").textContent = s.title;
  $("scenario-purpose").textContent = s.category === "safety" ? "Verifies that untrusted customer text cannot override purchase and policy rules." : "Compares the observed outcome and ordered tool trajectory with the golden fixture.";
  $("expected-outcome").textContent = label(s.expected.outcome); $("expected-total").textContent = money(s.expected.total_cents);
  $("customer-message").textContent = s.message;
  const facts = $("facts"); facts.replaceChildren();
  [["intent", s.intent], ["username", s.username], ["purchase", s.purchase_id], ["requested", s.requested_on]].forEach(([key, value]) => { const item = document.createElement("span"); item.className = "fact"; item.textContent = `${key}: ${text(value)}`; facts.append(item); });
  s.requested_items.forEach(i => { const item = document.createElement("span"); item.className = "fact"; item.textContent = `${i.quantity} × ${i.product_id}`; facts.append(item); });
}

function clearRun() {
  $("run-status").className = "status neutral"; $("run-status").textContent = "Not run";
  $("agent-response").textContent = "The response, recommended action, and safety boundary will appear here.";
  $("run-id").textContent = "No run ID"; $("overall-score").textContent = "—"; $("trace").replaceChildren(); $("trace").classList.remove("visible"); $("trace-empty").style.display = "flex";
  $("metrics").innerHTML = '<div class="metric-skeleton">Metrics appear after a run.</div>';
}

async function runSelected() {
  if (!state.selected) return showToast("Select a scenario first.");
  setRunning(true);
  try {
    const run = await api("/api/evaluate", { method: "POST", body: JSON.stringify({ scenario_id: state.selected.id }) });
    state.latest[run.scenario_id] = run; addHistory(run); renderRun(run); renderScenarios(); showToast(`${state.selected.title}: ${run.status}`);
  } catch (error) { showToast(error.message); }
  finally { setRunning(false); }
}

function setRunning(running) {
  const button = $("run"); button.disabled = running; button.textContent = running ? "Evaluating…" : "Run evaluation";
  if (running) { $("run-status").className = "status running"; $("run-status").textContent = "Running"; }
}

function renderRun(run) {
  $("run-status").className = `status ${run.status}`; $("run-status").textContent = run.status;
  $("agent-response").textContent = run.response; $("run-id").textContent = run.id; $("run-engine").textContent = `${run.engine} · ${run.duration_ms} ms`;
  $("overall-score").textContent = `${Math.round(run.composite_score * 100)}%`; renderTrace(run.trace); renderMetrics(run.metrics);
}

function renderTrace(events) {
  const list = $("trace"); list.replaceChildren(); $("trace-empty").style.display = "none"; list.classList.add("visible");
  events.forEach(event => {
    const li = document.createElement("li"); li.className = "trace-event";
    const detail = JSON.stringify({ input: event.input, output: event.output, citations: event.citation_ids }, null, 2);
    li.innerHTML = `<span class="trace-dot">✓</span><button class="trace-summary"><strong></strong><span></span></button><p></p><pre class="trace-detail"></pre>`;
    li.querySelector("strong").textContent = `${event.order}. ${label(event.name)}`; li.querySelector(".trace-summary span").textContent = event.type;
    li.querySelector("p").textContent = event.summary; li.querySelector("pre").textContent = detail;
    li.querySelector("button").addEventListener("click", () => li.classList.toggle("open")); list.append(li);
  });
}

function renderMetrics(metrics) {
  const grid = $("metrics"); grid.replaceChildren();
  metrics.forEach(metric => {
    const card = document.createElement("div"); card.className = "metric-card";
    card.innerHTML = `<div class="metric-head"><strong></strong><span></span></div><p></p><div class="metric-bar"><div class="metric-fill"></div></div><div class="metric-footer"><span></span><span>local evaluator</span></div>`;
    card.querySelector("strong").textContent = metric.label; card.querySelector(".metric-head span").textContent = metric.score.toFixed(2);
    card.querySelector("p").textContent = metric.explanation; card.querySelector(".metric-fill").style.width = `${metric.score * 100}%`;
    card.querySelector(".metric-footer span").textContent = metric.passed ? "PASS · threshold 1.0" : "FAIL · threshold 1.0";
    if (!metric.passed) card.querySelector(".metric-fill").style.background = "var(--danger)"; grid.append(card);
  });
}

function addHistory(run) {
  state.history.unshift({ id: run.id, scenarioId: run.scenario_id, title: state.selected?.title || run.scenario_id, status: run.status, score: run.composite_score, createdAt: run.created_at });
  state.history = state.history.slice(0, 20); saveHistory(); renderHistory();
}
function renderHistory() {
  $("history-count").textContent = state.history.length;
  const passed = state.history.filter(x => x.status === "passed").length; $("history-rate").textContent = state.history.length ? `${Math.round(passed / state.history.length * 100)}%` : "—";
  $("history-latest").textContent = state.history.length ? `${Math.round(state.history[0].score * 100)}%` : "—";
  const list = $("history"); list.replaceChildren();
  if (!state.history.length) { const empty = document.createElement("div"); empty.className = "empty-history"; empty.textContent = "Completed evaluations will appear here."; list.append(empty); return; }
  state.history.forEach(item => {
    const row = document.createElement("div"); row.className = "history-row"; row.innerHTML = `<strong></strong><span></span><span></span><span></span>`;
    row.children[0].textContent = item.title; row.children[1].textContent = item.id; row.children[2].textContent = new Date(item.createdAt).toLocaleString(); row.children[3].textContent = `${item.status.toUpperCase()} · ${Math.round(item.score * 100)}%`; row.children[3].className = item.status === "passed" ? "history-pass" : "history-fail"; list.append(row);
  });
}

async function runAll() {
  const button = $("run-all"); button.disabled = true; button.textContent = "Running suite…";
  try {
    const report = await api("/api/evaluate-all", { method: "POST", body: "{}" });
    report.results.forEach(run => { state.latest[run.scenario_id] = run; const scenario = state.scenarios.find(s => s.id === run.scenario_id); state.history.unshift({ id: run.id, scenarioId: run.scenario_id, title: scenario?.title || run.scenario_id, status: run.status, score: run.composite_score, createdAt: run.created_at }); });
    state.history = state.history.slice(0, 20); saveHistory(); renderHistory(); renderScenarios();
    $("suite-health").textContent = report.failed ? `${report.failed} regression${report.failed === 1 ? "" : "s"}` : "All gates pass"; $("suite-score").textContent = `${report.passed}/${report.total}`;
    if (state.selected && state.latest[state.selected.id]) renderRun(state.latest[state.selected.id]); showToast(`Suite complete: ${report.passed}/${report.total} passed`);
  } catch (error) { showToast(error.message); }
  finally { button.disabled = false; button.textContent = "Run all 8 scenarios"; }
}

function closeSidebar() { $("sidebar").classList.remove("open"); $("scrim").classList.remove("open"); }
function bind() {
  $("run").addEventListener("click", runSelected); $("run-all").addEventListener("click", runAll);
  $("reset").addEventListener("click", () => { state.latest = {}; clearRun(); renderScenarios(); showToast("Current run state reset."); });
  $("search").addEventListener("input", e => { state.search = e.target.value; renderScenarios(); });
  document.querySelectorAll(".filter").forEach(button => button.addEventListener("click", () => { document.querySelectorAll(".filter").forEach(x => x.classList.remove("active")); button.classList.add("active"); state.filter = button.dataset.filter; renderScenarios(); }));
  $("expand-all").addEventListener("click", () => { const events = [...document.querySelectorAll(".trace-event")]; const open = events.some(x => !x.classList.contains("open")); events.forEach(x => x.classList.toggle("open", open)); $("expand-all").textContent = open ? "Collapse all" : "Expand all"; });
  $("clear-history").addEventListener("click", () => { state.history = []; saveHistory(); renderHistory(); showToast("Local history cleared."); });
  $("mobile-menu").addEventListener("click", () => { $("sidebar").classList.add("open"); $("scrim").classList.add("open"); }); $("sidebar-close").addEventListener("click", closeSidebar); $("scrim").addEventListener("click", closeSidebar);
  $("engine-info").addEventListener("click", () => $("engine-dialog").showModal()); $("dialog-close").addEventListener("click", () => $("engine-dialog").close());
  document.addEventListener("keydown", event => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runSelected(); if (event.key === "Escape") closeSidebar(); });
}

async function init() {
  bind(); renderHistory();
  try { const data = await api("/api/scenarios"); state.scenarios = data.scenarios; renderScenarios(); if (state.scenarios.length) await selectScenario(state.scenarios[0].id); }
  catch (error) { showToast(`Could not load scenarios: ${error.message}`); $("scenario-list").innerHTML = '<div class="empty-history">API unavailable. Start the local server and retry.</div>'; }
}
init();
