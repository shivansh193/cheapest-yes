// Shared helpers and the PayPal checkout widget used by the store and the replay.
export const $ = (s, el = document) => el.querySelector(s);
export const $$ = (s, el = document) => [...el.querySelectorAll(s)];
export const money = (v) => (Number(v) < 0 ? "−$" : "$") + Math.abs(Number(v)).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const pct = (v, d = 0) => (v * 100).toFixed(d) + "%";
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const LABELS = { none: "No incentive", paylater: "PayPal Pay Later", free_shipping: "Free shipping", addon: "Free add-on", discount_5: "5% off", discount_10: "10% off" };
export const incColor = (k) => getComputedStyle(document.documentElement).getPropertyValue(`--inc-${k}`).trim() || "#888";

export async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || r.statusText);
  return j;
}

export function nav(active) {
  const links = [["/", "Store"], ["/replay", "Shopper replay"], ["/dashboard", "Merchant dashboard"], ["/docs", "API"]];
  document.body.insertAdjacentHTML("afterbegin", `
  <div class="topbar"><div class="inner">
    <a class="brand" href="/" style="text-decoration:none"><span class="brand-mark">✓</span>Cheapest Yes</a>
    <nav class="nav">${links.map(([h, t]) => `<a href="${h}" class="${h === active ? "active" : ""}">${t}</a>`).join("")}</nav>
    <span class="sandbox-pill" title="All payments run in the PayPal sandbox. No real money moves.">PayPal sandbox · test money only</span>
  </div></div>`);
}

let _config, _sdk;
export async function config() { return (_config ||= await api("/api/config")); }

export async function loadPayPal() {
  if (_sdk) return _sdk;
  const c = await config();
  _sdk = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(c.paypal_client_id)}&currency=USD&intent=capture` +
      `&components=buttons,messages,funding-eligibility&enable-funding=paylater&buyer-country=US`;
    s.dataset.namespace = "paypal";
    s.onload = () => resolve(window.paypal);
    s.onerror = () => reject(new Error("PayPal SDK failed to load"));
    document.head.appendChild(s);
  });
  return _sdk;
}

/** Render the incentive slot for a decision into `el`. */
export function incentiveHTML(d, addon) {
  const a = d.amounts;
  const per4 = (a.total / 4).toFixed(2);
  const why = `<details class="why"><summary>Why am I seeing this?</summary>
      This store picks at most one offer per checkout from your activity in this visit (cart, time on page, clicks),
      never from who you are or where you live. Prices never go above list.</details>`;
  switch (d.incentive) {
    case "paylater":
      return `<div class="incentive paylater"><div class="headline">Split it into 4 interest-free payments of ${money(per4)}</div>
        <div class="small muted">PayPal Pay Later: pay ${money(per4)} today, then every 2 weeks. No change to the price.</div>
        <div id="pp-message" style="margin-top:8px"></div>${why}</div>`;
    case "free_shipping":
      return `<div class="incentive free_shipping"><div class="headline">Shipping is on us today</div>
        <div class="small muted">Free shipping applied: you save ${money(8.99)}.</div>${why}</div>`;
    case "addon":
      return `<div class="incentive addon"><div class="row">${addon?.image ? `<img src="${esc(addon.image)}" alt="" style="width:48px;height:48px;object-fit:contain;background:#fff;border-radius:8px">` : ""}
        <div><div class="headline">Free gift with this order</div><div class="small muted">${esc(addon?.title || "Travel case")} (${money(addon?.price || 19)} value), added at $0.00.</div></div></div>${why}</div>`;
    case "discount_5":
    case "discount_10":
      return `<div class="incentive ${d.incentive}"><div class="headline">${d.incentive === "discount_5" ? "5%" : "10%"} off this order</div>
        <div class="small muted">You save ${money(a.discount)}. Applied automatically.</div>${why}</div>`;
    default:
      return "";
  }
}

export function totalsHTML(d) {
  const a = d.amounts;
  return `<div class="line"><span>Subtotal</span><span class="num">${money(a.item_total)}</span></div>
    <div class="line"><span>Shipping</span><span class="num">${a.shipping ? money(a.shipping) : "<b style='color:var(--good)'>Free</b>"}</span></div>
    ${d.incentive === "addon" ? `<div class="line"><span>Free gift</span><span class="num">$0.00</span></div>` : ""}
    ${a.discount ? `<div class="line"><span>Discount</span><span class="num" style="color:var(--good)">−${money(a.discount)}</span></div>` : ""}
    <div class="line total"><span>Total</span><span class="num">${money(a.total)}</span></div>`;
}

/** Mount PayPal buttons (and Pay Later messaging when that's the incentive) for a logged decision. */
export async function mountCheckout(d, { buttons, onPaid, onError }) {
  const paypal = await loadPayPal();
  const msg = document.getElementById("pp-message");
  if (msg && d.incentive === "paylater") {
    paypal.Messages({ amount: d.amounts.total, placement: "payment", style: { layout: "text", logo: { type: "inline" } } }).render(msg).catch(() => {
      msg.innerHTML = `<span class="small muted">(PayPal's message didn't render here; the offer above is the same.)</span>`;
    });
  }
  buttons.innerHTML = "";
  let orderId = null;
  await paypal.Buttons({
    style: { layout: "vertical", shape: "rect", label: "paypal" },
    createOrder: async () => (orderId = (await api("/api/checkout/orders", { decision_id: d.decision_id })).id),
    onApprove: async (data) => {
      const cap = await api(`/api/checkout/orders/${data.orderID}/capture`, { funding_source: data.paymentSource || null });
      onPaid?.(cap);
    },
    onError: (e) => onError?.(e),
    onCancel: () => {},
  }).render(buttons);
}

export function receiptHTML(cap) {
  return `<div class="receipt"><h3>Paid in the PayPal sandbox ✓</h3>
    <div class="small" style="margin-top:6px">Order <span class="mono">${esc(cap.order_id)}</span><br>
    Capture <span class="mono">${esc(cap.capture_id)}</span> · ${esc(cap.status)}<br>
    Amount ${money(cap.amount.value)} · PayPal fee ${money(cap.paypal_fee)} · merchant net ${money(cap.net || 0)}</div>
    <div class="small muted" style="margin-top:6px">Logged against decision <span class="mono">${esc(cap.decision_id)}</span>. See it in the <a href="/dashboard">merchant dashboard</a>.</div></div>`;
}
