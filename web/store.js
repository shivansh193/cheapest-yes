import { $, api, esc, money, nav, config, incentiveHTML, totalsHTML, mountCheckout, receiptHTML } from "./common.js";

nav("/");

// ---------------------------------------------------------------- session signals (behaviour only)
const store = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch { return null; } };
const shopperId = store("cy_shopper") || (() => { const id = "s_" + crypto.randomUUID(); store("cy_shopper", id); return id; })();
const isReturning = store("cy_seen") ? 1 : 0;
store("cy_seen", "1");
const sig = {
  product_views: 0, accessory_views: 0, compare_events: 0, cart_returns: 0, browse_ms: 0,
  hesitation_after_shipping_s: 0, hesitation_after_total_s: 0, checkout_started: 0,
};
let cartOpens = 0;
document.addEventListener("copy", () => sig.compare_events++);
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") sig.compare_events++; });
const isMobile = matchMedia("(pointer: coarse)").matches || innerWidth < 768 ? 1 : 0;

// ---------------------------------------------------------------- catalog + cart
let products = [], addon = null;
const cart = new Map(); // id -> qty
const byId = (id) => products.find((p) => p.id === id);
const cartItems = () => [...cart].map(([id, qty]) => ({ ...byId(id), qty }));
const cartTotal = () => cartItems().reduce((s, i) => s + i.price * i.qty, 0);
const updateCount = () => ($("#cart-count").textContent = [...cart.values()].reduce((a, b) => a + b, 0));

async function init() {
  const cat = await api("/api/products");
  products = cat.products; addon = cat.addon;
  $("#products").innerHTML = products.map((p) => `
    <article class="card product" data-id="${p.id}">
      <div class="img"><img loading="lazy" src="${esc(p.image)}" alt="${esc(p.title)}"></div>
      <div class="body"><div class="brandname">${esc(p.brand)} · ${esc(p.category)}</div>
        <div class="title">${esc(p.title)}</div><div class="price num">${money(p.price)}</div></div>
    </article>`).join("");
  $("#products").addEventListener("click", (e) => { const c = e.target.closest(".product"); if (c) openProduct(c.dataset.id); });
  $("#open-cart").addEventListener("click", openCart);
}

function openProduct(id) {
  const p = byId(id);
  sig.product_views++;
  if (p.category === "Accessories") sig.accessory_views++;
  const t0 = performance.now();
  $("#modal-root").innerHTML = `<div class="drawer-backdrop" data-close></div><div class="modal"><div class="card">
    <div class="pdp"><div class="img"><img src="${esc(p.image)}" alt="${esc(p.title)}"></div>
    <div class="stack"><div class="brandname muted small" style="text-transform:uppercase;font-weight:600">${esc(p.brand)}</div>
      <h2>${esc(p.title)}</h2><div style="font-size:22px;font-weight:750" class="num">${money(p.price)}</div>
      <p class="small muted">${esc(p.description)}</p>
      ${p.features?.length ? `<ul class="small" style="padding-left:18px;margin:0">${p.features.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>` : ""}
      <div class="row"><button class="btn primary" id="add">Add to cart</button><button class="btn" data-close>Close</button></div>
      <div class="small muted">Source: Channel3 product catalog</div></div></div></div></div>`;
  const close = () => { sig.browse_ms += performance.now() - t0; $("#modal-root").innerHTML = ""; };
  $("#modal-root").querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", close));
  $("#add").addEventListener("click", () => { cart.set(id, (cart.get(id) || 0) + 1); updateCount(); close(); openCart(); });
}

// ---------------------------------------------------------------- checkout flow
let step = 0, revealAt = 0, checkoutStart = 0, decision = null;

function openCart() {
  cartOpens++;
  if (cartOpens > 1) sig.cart_returns++;
  step = 0;
  renderDrawer();
}

function closeDrawer() {
  if (decision && step === 3) api(`/api/checkout/abandon/${decision.decision_id}`, {}).catch(() => {});
  $("#drawer-root").innerHTML = "";
}

function renderDrawer() {
  const items = cartItems();
  const sub = cartTotal();
  const body = !items.length
    ? `<p class="muted">Your cart is empty.</p>`
    : `<div class="steps"><span class="${step >= 1 ? "on" : ""}"></span><span class="${step >= 2 ? "on" : ""}"></span><span class="${step >= 3 ? "on" : ""}"></span></div>
      ${items.map((i) => `<div class="cart-item"><img src="${esc(i.image)}" alt=""><div><div class="small" style="font-weight:600">${esc(i.title)}</div>
        <div class="small muted">Qty ${i.qty}${step === 0 ? ` · <a href="#" data-rm="${i.id}">remove</a>` : ""}</div></div><div class="num small">${money(i.price * i.qty)}</div></div>`).join("")}
      <div style="margin-top:12px" id="totals">
        <div class="line"><span>Subtotal</span><span class="num">${money(sub)}</span></div>
        ${step >= 1 ? `<div class="line"><span>Shipping</span><span class="num">${step === 3 ? "" : money(8.99)}</span></div>` : ""}
        ${step === 2 ? `<div class="line total"><span>Total</span><span class="num">${money(sub + 8.99)}</span></div>` : ""}
      </div>
      <div id="step-body" style="margin-top:14px"></div>`;
  $("#drawer-root").innerHTML = `<div class="drawer-backdrop" id="bd"></div><aside class="drawer" aria-label="Cart">
    <header><h2>${["Cart", "Shipping", "Review", "Pay"][step]}</h2><button class="btn" id="x">Close</button></header>
    <div class="content">${body}</div></aside>`;
  $("#bd").onclick = $("#x").onclick = closeDrawer;
  $("#drawer-root").querySelectorAll("[data-rm]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); cart.delete(a.dataset.rm); updateCount(); renderDrawer(); }));
  if (!items.length) return;
  const sb = $("#step-body");
  if (step === 0) {
    sb.innerHTML = `<button class="btn primary block" id="go">Checkout</button>`;
    $("#go").onclick = () => { checkoutStart = performance.now(); step = 1; revealAt = performance.now(); renderDrawer(); };
  } else if (step === 1) {
    sb.innerHTML = `<p class="small muted">Standard shipping, 3–5 business days.</p><button class="btn primary block" id="go">Continue</button>`;
    $("#go").onclick = () => { sig.hesitation_after_shipping_s = (performance.now() - revealAt) / 1000; step = 2; revealAt = performance.now(); renderDrawer(); };
  } else if (step === 2) {
    sb.innerHTML = `<button class="btn primary block" id="go">Continue to payment</button>`;
    $("#go").onclick = async () => { sig.hesitation_after_total_s = (performance.now() - revealAt) / 1000; await decide(); };
  }
}

async function decide() {
  $("#step-body").innerHTML = `<div class="row muted"><span class="spinner"></span> Preparing checkout…</div>`;
  const session = {
    time_on_page_s: +((performance.now() - checkoutStart) / 1000).toFixed(1),
    product_views: sig.product_views, cart_returns: sig.cart_returns, compare_events: sig.compare_events,
    hesitation_after_shipping_s: +sig.hesitation_after_shipping_s.toFixed(1), hesitation_after_total_s: +sig.hesitation_after_total_s.toFixed(1),
    accessory_views: sig.accessory_views, is_mobile: isMobile, is_returning: isReturning,
    prior_orders: +(store("cy_orders") || 0), browse_seconds: +(sig.browse_ms / 1000).toFixed(1),
  };
  try {
    decision = await api("/api/store/decide", { cart: cartItems().map((i) => ({ id: i.id, title: i.title, price: i.price, qty: i.qty })), session, shopper_id: shopperId });
  } catch (e) {
    $("#step-body").innerHTML = `<p style="color:var(--bad)">Couldn't start checkout: ${esc(e.message)}</p>`;
    return;
  }
  step = 3;
  renderDrawer();
  $("#totals").innerHTML = totalsHTML(decision);
  $("#step-body").innerHTML = `${incentiveHTML(decision, addon)}<div id="paypal-buttons"></div>
    <div class="notice">Sandbox checkout: log in with a PayPal <b>sandbox</b> personal account (from developer.paypal.com → Sandbox accounts).</div>`;
  mountCheckout(decision, {
    buttons: $("#paypal-buttons"),
    onPaid: (cap) => {
      store("cy_orders", String(+(store("cy_orders") || 0) + 1));
      cart.clear(); updateCount();
      $("#step-body").innerHTML = receiptHTML(cap);
      step = 4;
    },
    onError: (e) => { $("#paypal-buttons").insertAdjacentHTML("afterend", `<p class="small" style="color:var(--bad)">PayPal error: ${esc(e?.message || e)}</p>`); },
  }).catch((e) => { $("#paypal-buttons").innerHTML = `<p class="small" style="color:var(--bad)">${esc(e.message)}</p>`; });
}

config();
init();
