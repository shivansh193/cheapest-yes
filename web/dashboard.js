import { $, api, esc, money, pct, nav, LABELS, incColor } from "./common.js";

nav("/dashboard");
const dark = matchMedia("(prefers-color-scheme: dark)").matches;
if (dark) $("#grid").className = "ag-theme-quartz-dark";
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
Chart.defaults.font.family = "Inter, system-ui, sans-serif";
Chart.defaults.color = css("--muted");
Chart.defaults.borderColor = css("--line");

const k = (n) => (Math.abs(n) >= 1000 ? (n / 1000).toFixed(1) + "k" : Math.round(n).toString());
const sgn = (n) => (n >= 0 ? "+" : "−") + "$" + k(Math.abs(n));

async function load() {
  const st = await api("/api/stats");
  renderKPIs(st.eval);
  renderPolicies(st.eval);
  renderMix(st.mix);
  renderFair(st.fairness, st.eval);
  renderBudget(st.budget, st.sandbox_payments);
}

function renderKPIs(ev) {
  if (!ev) { $("#kpis").innerHTML = `<div class="card pad">Run <span class="mono">make eval</span> to populate.</div>`; return; }
  const P = ev.sim.policies, cy = P["Cheapest Yes"], nopl = P["Cheapest Yes without Pay Later"], bl = P["Blanket 10% off"];
  $("#nshop").textContent = ev.sim.n_shoppers.toLocaleString();
  const ci = (a) => `95% CI ${sgn(a[0])} to ${sgn(a[1])}`;
  const cards = [
    ["Profit lift vs blanket 10% off", sgn(cy.lift_vs_blanket_per_1k), `per 1,000 shoppers · ${ci(cy.lift_vs_blanket_ci)}`, true],
    ["Profit lift vs no incentive", sgn(cy.lift_vs_none_per_1k), `per 1,000 shoppers · ${ci(cy.lift_vs_none_ci)}`, true],
    ["What Pay Later contributes", sgn(cy.profit_per_1k - nopl.profit_per_1k), `profit lost per 1,000 shoppers if Pay Later is removed from the ladder`, true],
    ["Incentive spend wasted", `$${k(cy.leakage_per_1k)}`, `per 1,000 shoppers on would-buy-anyway shoppers, vs $${k(bl.leakage_per_1k)} for a blanket 10% off`, false],
  ];
  $("#kpis").innerHTML = cards.map(([l, v, s, g]) => `<div class="card pad kpi"><div class="label">${l}</div><div class="value ${g ? "good" : ""}">${v}</div><div class="sub">${s}</div></div>`).join("");
}

function renderPolicies(ev) {
  if (!ev) return;
  const P = ev.sim.policies;
  const names = Object.keys(P);
  const color = (n) => (n === "Cheapest Yes" ? css("--accent") : n.startsWith("Oracle") ? css("--line") : n.includes("without") ? css("--inc-addon") : css("--inc-none"));
  new Chart($("#policy-chart"), {
    type: "bar",
    data: { labels: names, datasets: [{ data: names.map((n) => P[n].profit_per_1k), backgroundColor: names.map(color), borderRadius: 6 }] },
    options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false },
      tooltip: { callbacks: { label: (c) => { const r = P[c.label]; return [`$${r.profit_per_1k.toLocaleString()} (95% CI $${r.profit_per_1k_ci[0].toLocaleString()}–$${r.profit_per_1k_ci[1].toLocaleString()})`,
        `conversion ${pct(r.conversion, 1)} · offers to ${pct(r.offer_rate)} · spend $${r.incentive_spend_per_1k.toLocaleString()}`]; } } } },
      scales: { x: { ticks: { callback: (v) => "$" + k(v) }, grid: { color: css("--line") } }, y: { grid: { display: false } } } },
  });
  $("#policy-note").textContent = `Cheapest Yes picks the same incentive as an oracle that sees the hidden truth for ${pct(ev.sim.agreement_with_oracle)} of shoppers. Intent model AUC ${ev.intent.auc.toFixed(3)} on public UCI data` +
    (ev.criteo ? `; uplift method ranks ${ev.criteo.auuc_ratio_vs_random}× better than random on Criteo.` : ".");
}

function renderMix(mix) {
  const order = Object.keys(LABELS);
  const m = order.map((k) => mix.find((r) => r.incentive === k) || { incentive: k, n: 0, bought: 0, settled: 0 });
  const total = m.reduce((s, r) => s + r.n, 0);
  new Chart($("#mix-chart"), {
    type: "doughnut",
    data: { labels: m.map((r) => LABELS[r.incentive]), datasets: [{ data: m.map((r) => r.n), backgroundColor: m.map((r) => incColor(r.incentive)), borderWidth: 0 }] },
    options: { maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "right", labels: { boxWidth: 10, boxHeight: 10 } },
      tooltip: { callbacks: { label: (c) => { const r = m[c.dataIndex]; return `${r.n} decisions (${pct(r.n / total)}) · ${r.settled ? pct(r.bought / r.settled) : "–"} bought`; } } } } },
  });
  $("#mix-note").textContent = `${total.toLocaleString()} logged decisions. "No incentive" is a decision too: margin kept on shoppers likely to buy anyway.`;
}

function renderFair(rows, ev) {
  const sim = ev?.sim?.fairness || {};
  $("#fair").innerHTML = `<tr><th>Group</th><th>Offer rate (log)</th><th>Discount rate (log)</th><th>Offer rate (sim)</th></tr>` +
    rows.map((r) => `<tr><td>${esc(r.grp)}</td><td class="num">${r.offer_rate == null ? "–" : pct(r.offer_rate)}</td><td class="num">${r.discount_rate == null ? "–" : pct(r.discount_rate)}</td>
      <td class="num">${sim[r.grp] ? pct(sim[r.grp].offer_rate) : "–"}</td></tr>`).join("");
}

function renderBudget(b, paid) {
  $("#budget-used").textContent = money(b.spent_today) + " used";
  $("#budget-limit").textContent = "of " + money(b.limit);
  $("#budget-bar").style.width = Math.min(100, (100 * b.spent_today) / b.limit).toFixed(1) + "%";
  $("#guard").innerHTML = `<div class="line"><span>Live decisions today</span><b class="num">${b.decisions_today}</b></div>
    <div class="line"><span>Sandbox payments captured</span><b class="num">${paid.n}</b></div>
    <div class="line"><span>PayPal fees on those</span><b class="num">${money(paid.fees)}</b></div>
    <div class="line"><span>Max discount</span><b>10%</b></div><div class="line"><span>Offers per shopper / 7 days</span><b>2</b></div>
    <div class="line"><span>Price above list</span><b style="color:var(--good)">never (tested)</b></div>`;
}

// ---------------------------------------------------------------- AG Grid decision log
const incCell = (p) => p.value ? `<span class="tag"><span class="dot" style="background:${incColor(p.value)}"></span>${esc(LABELS[p.value])}</span>` : "";
const pchosen = (d) => (d.options || []).find((o) => o.incentive === d.incentive)?.p_buy;
const pnone = (d) => (d.options || []).find((o) => o.incentive === "none")?.p_buy;
const gridOptions = {
  columnDefs: [
    { field: "created_at", headerName: "Time", width: 150, sort: "desc", valueFormatter: (p) => new Date(p.value).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) },
    { field: "source", width: 105, filter: true },
    { field: "persona", headerName: "Shopper", width: 160, filter: true, valueFormatter: (p) => p.value || "live shopper" },
    { field: "item_total", headerName: "Cart", width: 95, type: "numericColumn", valueFormatter: (p) => money(p.value) },
    { headerName: "P(buy) none", width: 115, type: "numericColumn", valueGetter: (p) => pnone(p.data), valueFormatter: (p) => (p.value == null ? "" : pct(p.value)) },
    { field: "incentive", headerName: "Chosen", width: 170, cellRenderer: incCell, filter: true },
    { headerName: "P(buy) chosen", width: 125, type: "numericColumn", valueGetter: (p) => pchosen(p.data), valueFormatter: (p) => (p.value == null ? "" : pct(p.value)) },
    { field: "expected_gain", headerName: "Exp. gain", width: 105, type: "numericColumn", valueFormatter: (p) => (p.value == null ? "" : (p.value >= 0 ? "+" : "") + money(p.value)) },
    { field: "outcome", width: 105, filter: true, cellStyle: (p) => ({ color: p.value === "bought" ? css("--good") : p.value === "abandoned" ? css("--muted") : css("--warn"), fontWeight: 600 }) },
    { field: "funding_source", headerName: "Paid with", width: 105 },
    { field: "realized_profit", headerName: "Profit", width: 95, type: "numericColumn", valueFormatter: (p) => (p.value == null ? "" : money(p.value)) },
    { field: "paypal_order_id", headerName: "PayPal order", width: 170, cellClass: "mono" },
    { field: "paypal_capture_id", headerName: "Capture", width: 170, cellClass: "mono" },
    { field: "paypal_fee", headerName: "PayPal fee", width: 105, type: "numericColumn", valueFormatter: (p) => (p.value == null ? "" : money(p.value)) },
    { headerName: "Why", flex: 1, minWidth: 380, wrapText: true, autoHeight: true, valueGetter: (p) => p.data.llm_explanation || p.data.explanation,
      tooltipValueGetter: (p) => (p.data.reasons || []).map((r) => r.text).join("; ") },
  ],
  defaultColDef: { resizable: true, sortable: true },
  rowData: [],
  pagination: true,
  paginationPageSize: 50,
  paginationPageSizeSelector: [25, 50, 100, 200],
  tooltipShowDelay: 300,
  getRowStyle: (p) => (p.data.source !== "simulated" ? { background: css("--accent-soft") } : null),
};
const grid = agGrid.createGrid($("#grid"), gridOptions);
async function loadRows() {
  const src = $("#source").value;
  grid.setGridOption("rowData", await api(`/api/decisions?limit=2000${src ? "&source=" + src : ""}`));
}
$("#filter").addEventListener("input", (e) => grid.setGridOption("quickFilterText", e.target.value));
$("#source").addEventListener("change", loadRows);

// ---------------------------------------------------------------- copilot
const SUGGEST = ["Why did we show Pay Later to so many carts yesterday?", "Which incentive made the most profit?", "Are mobile shoppers getting more discounts?"];
$("#suggest").innerHTML = SUGGEST.map((s) => `<button class="chip small" type="button">${esc(s)}</button>`).join("");
$("#suggest").addEventListener("click", (e) => { const b = e.target.closest(".chip"); if (b) { $("#q").value = b.textContent; ask(); } });
$("#ask").addEventListener("submit", (e) => { e.preventDefault(); ask(); });
async function ask() {
  const q = $("#q").value.trim() || $("#q").placeholder;
  $("#answer").innerHTML = `<span class="row muted small"><span class="spinner"></span> Thinking…</span>`;
  try {
    const r = await api("/api/copilot", { question: q });
    $("#answer").innerHTML = `${esc(r.answer)}${r.model ? `<div class="small muted" style="margin-top:6px">${esc(r.model)} · answered from decision-log aggregates</div>` : ""}`;
  } catch (e) { $("#answer").textContent = e.message; }
}

load();
loadRows();
