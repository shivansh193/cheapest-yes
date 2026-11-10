import { $, api, esc, money, pct, nav, LABELS, incColor, config, incentiveHTML, totalsHTML, mountCheckout, receiptHTML } from "./common.js";

nav("/replay");

const BLURB = {
  "split-payment person": "Big cart, stalls when the total appears",
  "will buy anyway": "Returning customer who knows what they want",
  "free-shipping hunter": "Small cart, balks at the shipping line",
  "price-sensitive student": "Compares prices in other tabs",
  "bundle lover": "Keeps browsing accessories",
  "just browsing": "Window-shopping, low intent",
};
let running = 0, addon = null;

async function init() {
  const [ps, cat] = await Promise.all([api("/api/personas"), api("/api/products")]);
  addon = cat.addon;
  $("#personas").innerHTML = ps.map((p) => `<button class="chip" data-p="${esc(p.name)}" title="${esc(BLURB[p.name] || "")}">${esc(p.name)}</button>`).join("");
  $("#personas").addEventListener("click", (e) => { const b = e.target.closest("[data-p]"); if (b) run(b.dataset.p, b); });
  const q = new URLSearchParams(location.search).get("persona");
  if (q) run(q, [...document.querySelectorAll("[data-p]")].find((b) => b.dataset.p === q));
}

function events(s) {
  // A readable session timeline built from the signals the engine actually receives.
  const ev = [];
  let t = 0;
  const add = (dt, text, signal) => { t += dt; ev.push({ t, text, signal }); };
  add(0, s.is_returning ? `Returning visitor${s.prior_orders ? ` (${s.prior_orders} past order${s.prior_orders > 1 ? "s" : ""})` : ""} lands on the store` : "New visitor lands on the store");
  add(2, `Browses ${s.product_views} product page${s.product_views === 1 ? "" : "s"}`);
  if (s.accessory_views) add(3, `Looks at ${s.accessory_views} accessor${s.accessory_views === 1 ? "y" : "ies"}`, true);
  if (s.compare_events) add(3, `${s.compare_events} price-comparison signal${s.compare_events > 1 ? "s" : ""} (copies a product name, switches tabs)`, true);
  add(4, `Adds ${s.n_items} item${s.n_items > 1 ? "s" : ""} to cart (${money(s.cart_value)})`);
  if (s.cart_returns) add(5, `Leaves and comes back to the cart ${s.cart_returns}×`, s.cart_returns > 1);
  add(3, "Starts checkout; shipping cost ($8.99) appears");
  add(Math.max(1, s.hesitation_after_shipping_s), `Pauses ${s.hesitation_after_shipping_s.toFixed(0)}s on the shipping line`, s.hesitation_after_shipping_s >= 8);
  add(1, `Order total ${money(s.cart_value + 8.99)} appears`);
  add(Math.max(1, s.hesitation_after_total_s), `Pauses ${s.hesitation_after_total_s.toFixed(0)}s on the total`, s.hesitation_after_total_s >= 8);
  add(1, `Device: ${s.is_mobile ? "mobile" : "desktop"} · intent model score ${s.intent_score.toFixed(2)}`);
  return ev;
}

async function run(persona, btn) {
  const my = ++running;
  document.querySelectorAll("[data-p]").forEach((b) => b.classList.toggle("active", b === btn));
  $("#timeline").innerHTML = ""; $("#cart").innerHTML = ""; $("#checkout-card").classList.add("hidden");
  $("#decision").innerHTML = `<div class="row muted"><span class="spinner"></span> Simulating a ${esc(persona)}…</div>`;
  let d;
  try { d = await api("/api/replay", { persona }); } catch (e) { $("#decision").innerHTML = `<p style="color:var(--bad)">${esc(e.message)}</p>`; return; }
  if (my !== running) return;
  const s = d.session;
  $("#cart").innerHTML = d.cart.map((i) => `<div class="cart-item"><img src="${esc(i.image)}" alt=""><div class="small" style="font-weight:600">${esc(i.title)}</div><div class="num small">${money(i.price)}</div></div>`).join("");
  const ev = events(s);
  $("#timeline").innerHTML = ev.map((e) => `<li><span class="t">${fmtT(e.t)}</span><span class="${e.signal ? "sig" : ""}">${esc(e.text)}</span></li>`).join("");
  $("#decision").innerHTML = `<div class="row muted"><span class="spinner"></span> Watching the session…</div>`;
  const lis = [...document.querySelectorAll("#timeline li")];
  for (let i = 0; i < lis.length; i++) {
    await new Promise((r) => setTimeout(r, 420));
    if (my !== running) return;
    lis[i].classList.add("show");
    $("#clock").textContent = fmtT(ev[i].t);
  }
  showDecision(d, persona, my);
}

const fmtT = (t) => `${Math.floor(t / 60)}:${String(Math.round(t % 60)).padStart(2, "0")}`;

function showDecision(d, persona, my) {
  const chosen = d.options.find((o) => o.incentive === d.incentive);
  const pNone = d.options.find((o) => o.incentive === "none").p_buy;
  const truth = d.hidden_truth.p_buy;
  $("#decision").innerHTML = `
    <div class="row between wrap"><div class="verdict"><span class="dot" style="width:14px;height:14px;background:${incColor(d.incentive)}"></span>${esc(d.label)}</div>
      <span class="tag">expected profit ${d.expected_gain >= 0 ? "+" : ""}${money(d.expected_gain)} vs no incentive</span></div>
    <p style="margin:10px 0 6px">${esc(d.explanation)}</p>
    <div class="ai" id="ai"><span class="small muted">AI summary for the merchant</span><div id="ai-text" class="row muted small"><span class="spinner"></span> asking Gemini…</div></div>
    <h3 style="margin-top:16px">Top reasons (SHAP)</h3>
    <div>${d.reasons.map((r) => `<div class="reason"><span class="w">${r.contribution > 0 ? "+" : ""}${r.contribution.toFixed(2)}</span><span>${esc(r.text)}</span></div>`).join("") || `<span class="muted small">No single strong signal.</span>`}</div>
    <h3 style="margin-top:16px">Every option the engine scored</h3>
    <div style="overflow-x:auto"><table class="options"><thead><tr><th>Incentive</th><th>P(buy)</th><th></th><th>Profit if bought</th><th>Expected gain</th></tr></thead><tbody>
    ${d.options.map((o) => `<tr class="${o.incentive === d.incentive ? "chosen" : ""} ${o.allowed ? "" : "blocked"}">
      <td><span class="dot" style="background:${incColor(o.incentive)}"></span> ${esc(LABELS[o.incentive])}${o.allowed ? "" : `<div class="small muted">${esc(o.blocked_by)}</div>`}</td>
      <td class="num">${pct(o.p_buy)}</td>
      <td><div class="bar"><i style="width:${(o.p_buy * 100).toFixed(1)}%;background:${incColor(o.incentive)}"></i><b style="left:${(pNone * 100).toFixed(1)}%"></b></div></td>
      <td class="num">${money(o.profit_if_buy)}</td>
      <td class="num">${o.incentive === "none" ? "—" : (o.gain_vs_none >= 0 ? "+" : "") + money(o.gain_vs_none)}</td></tr>`).join("")}
    </tbody></table></div>
    <p class="small muted">Expected gain = P(buy | incentive) × profit if bought − P(buy | none) × profit if bought with nothing. Profit is after PayPal fees and, for Pay Later, the extra 1.5% fee weighted by how likely this shopper is to actually pay with it.</p>
    <details style="margin-top:10px"><summary><b>Reveal the hidden truth</b> (the engine never saw this)</summary>
      <p class="small" style="margin:8px 0">Hidden archetype: <b>${esc(d.hidden_truth.archetype)}</b>. True P(buy) by incentive:</p>
      <div class="row wrap small">${Object.entries(truth).map(([k, v]) => `<span class="tag"><span class="dot" style="background:${incColor(k)}"></span>${esc(LABELS[k])}: ${pct(v)}</span>`).join("")}</div>
      <p class="small muted">Browsing came from real UCI session: ${d.uci_session.ProductRelated} product pages, ${Math.round(d.uci_session.ProductRelated_Duration)}s, page value ${(+d.uci_session.PageValues).toFixed(1)}.</p></details>`;
  pollAI(d.decision_id, my);
  $("#checkout-card").classList.remove("hidden");
  $("#incentive").innerHTML = incentiveHTML(d, addon);
  $("#totals").innerHTML = totalsHTML(d);
  mountCheckout(d, {
    buttons: $("#paypal-buttons"),
    onPaid: (cap) => { $("#paypal-buttons").innerHTML = receiptHTML(cap); },
    onError: (e) => $("#paypal-buttons").insertAdjacentHTML("beforeend", `<p class="small" style="color:var(--bad)">${esc(e?.message || e)}</p>`),
  }).catch((e) => ($("#paypal-buttons").innerHTML = `<p class="small" style="color:var(--bad)">${esc(e.message)}</p>`));
}

async function pollAI(id, my) {
  for (let i = 0; i < 20; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    if (my !== running) return;
    const d = await api(`/api/decisions/${id}`).catch(() => null);
    if (d?.llm_explanation) { $("#ai-text").className = ""; $("#ai-text").textContent = d.llm_explanation; return; }
  }
  $("#ai-text").textContent = "Gemini didn't answer in time (free-tier quota). The deterministic explanation above is always shown.";
}

config();
init();
