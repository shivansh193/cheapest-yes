"""Cheapest Yes API and demo app."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from cy import sim  # noqa: E402
from cy.config import DEFAULT, INCENTIVES, LABELS  # noqa: E402
from cy.features import STORE_FEATURES  # noqa: E402
from cy.models import ARTIFACTS, get_bundle  # noqa: E402

from . import catalog, checkout, copilot, db, service  # noqa: E402
from . import paypal_client as pp  # noqa: E402

WEB = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(
    title="Cheapest Yes",
    version="1.0.0",
    description="Picks the cheapest incentive that turns a hesitant shopper into a buyer: PayPal Pay Later messaging, "
                "free shipping, a free add-on or a small discount, chosen to maximise the merchant's expected profit. "
                "List price is the ceiling: no response from this API ever raises a price.",
)


# ------------------------------------------------------------------ schemas
class CartItem(BaseModel):
    id: str = Field(..., description="Product id (catalog id for the demo store)")
    title: str = Field("", description="Product name")
    price: float = Field(..., ge=0, description="List price in USD")
    qty: int = Field(1, ge=1, le=20)
    brand: str | None = None
    image: str | None = None


class Session(BaseModel):
    time_on_page_s: float = Field(0, ge=0, description=STORE_FEATURES["time_on_page_s"])
    product_views: int = Field(0, ge=0, description=STORE_FEATURES["product_views"])
    cart_returns: int = Field(0, ge=0, description=STORE_FEATURES["cart_returns"])
    compare_events: int = Field(0, ge=0, description=STORE_FEATURES["compare_events"])
    hesitation_after_shipping_s: float = Field(0, ge=0, description=STORE_FEATURES["hesitation_after_shipping_s"])
    hesitation_after_total_s: float = Field(0, ge=0, description=STORE_FEATURES["hesitation_after_total_s"])
    accessory_views: int = Field(0, ge=0, description=STORE_FEATURES["accessory_views"])
    is_mobile: int = Field(0, ge=0, le=1, description=STORE_FEATURES["is_mobile"])
    is_returning: int = Field(0, ge=0, le=1, description=STORE_FEATURES["is_returning"])
    prior_orders: int = Field(0, ge=0, description=STORE_FEATURES["prior_orders"])
    browse_seconds: float | None = Field(None, ge=0, description="seconds spent on product pages (feeds the intent model)")
    intent_score: float | None = Field(None, ge=0, le=1, description="optional precomputed purchase-intent score")


class DecideRequest(BaseModel):
    cart: list[CartItem] = Field(..., min_length=1)
    session: Session = Field(default_factory=Session)
    shopper_id: str | None = Field(None, description="Opaque id for per-shopper caps; stored only as a hash")


class Option(BaseModel):
    incentive: str
    allowed: bool
    blocked_by: str | None
    p_buy: float
    p_paylater: float
    profit_if_buy: float
    expected_profit: float
    gain_vs_none: float
    expected_spend: float


class Amounts(BaseModel):
    item_total: float
    shipping: float
    discount: float
    total: float


class Reason(BaseModel):
    feature: str
    value: float
    contribution: float
    text: str


class DecideResponse(BaseModel):
    decision_id: str
    incentive: str = Field(..., description="one of: " + ", ".join(INCENTIVES))
    label: str
    amounts: Amounts
    expected_gain: float = Field(..., description="expected profit vs no incentive, USD")
    explanation: str
    reasons: list[Reason]
    options: list[Option]
    guardrails: list[str]


class OrderRequest(BaseModel):
    decision_id: str


class CaptureRequest(BaseModel):
    funding_source: str | None = Field(None, description="paymentSource reported by the PayPal JS SDK (paypal, paylater, card, venmo)")


class CopilotRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class ReplayRequest(BaseModel):
    persona: str = Field(..., description="one of GET /api/personas")
    seed: int | None = None


# ------------------------------------------------------------------ startup
@app.on_event("startup")
def _startup() -> None:
    db.init()
    get_bundle()
    threading.Thread(target=service.seed_simulated, daemon=True).start()


# ------------------------------------------------------------------ public API
@app.post("/decide", response_model=DecideResponse, tags=["Decisions"], summary="Choose the cheapest incentive for a cart", operation_id="decide")
def decide_endpoint(req: DecideRequest) -> dict:
    """Takes a cart and session-behaviour signals, returns the incentive with the highest expected
    profit (or none), the order amounts, and the reasons. Deterministic given the inputs and
    today's guardrail state. Amounts never exceed list price plus standard shipping."""
    out = service.run_decision([i.model_dump() for i in req.cart], req.session.model_dump(), "api", shopper_id=req.shopper_id)
    return out


@app.get("/health", tags=["Ops"], operation_id="getHealth")
def health() -> dict:
    return {"ok": True, "paypal": pp.API_BASE, "webhook_configured": bool(os.environ.get("PAYPAL_WEBHOOK_ID")),
            "models": get_bundle().meta}


# ------------------------------------------------------------------ demo store
@app.get("/api/config", tags=["Demo"])
def config() -> dict:
    return {"paypal_client_id": os.environ.get("PAYPAL_CLIENT_ID"), "currency": "USD", "buyer_country": "US",
            "shipping_fee": DEFAULT.shipping_fee, "labels": LABELS, "addon": catalog.catalog().get("addon"),
            "merchant": {k: getattr(DEFAULT, k) for k in ("gross_margin_rate", "max_discount_pct", "daily_incentive_budget",
                                                          "max_incentives_per_shopper_7d", "min_gain", "paylater_extra_pct")}}


@app.get("/api/products", tags=["Demo"])
def products(refresh: bool = False) -> dict:
    return catalog.catalog(refresh=refresh)


@app.post("/api/store/decide", response_model=DecideResponse, tags=["Demo"])
def store_decide(req: DecideRequest) -> dict:
    """Demo-store variant of /decide: cart prices are re-read from the catalog, never trusted from the browser."""
    cat = catalog.by_id()
    cart = []
    for i in req.cart:
        p = cat.get(i.id)
        if not p:
            raise HTTPException(400, f"unknown product {i.id}")
        cart.append({"id": p["id"], "title": p["title"], "brand": p["brand"], "price": p["price"], "image": p["image"], "qty": i.qty})
    return service.run_decision(cart, req.session.model_dump(), "store", shopper_id=req.shopper_id)


@app.get("/api/personas", tags=["Demo"])
def personas() -> list[dict]:
    return [{"name": k, "archetype": v} for k, v in sim.PERSONAS.items()]


@app.post("/api/replay", tags=["Demo"])
def replay(req: ReplayRequest) -> dict:
    """Generate a simulated shopper for a persona, map their cart onto real catalog products, and decide."""
    import numpy as np

    arch = sim.PERSONAS.get(req.persona)
    if not arch:
        raise HTTPException(400, "unknown persona")
    seed = req.seed if req.seed is not None else int(np.random.default_rng().integers(1, 1_000_000))
    s, _, truth = service.simulated_shopper(arch, seed, typical=True)
    cart = service.cart_for_value(s["cart_value"], np.random.default_rng(seed))
    d = service.run_decision(cart, s, "replay", shopper_id=f"replay-{req.persona}-{seed}", persona=req.persona)
    d["seed"] = seed
    d["uci_session"] = truth["uci"]
    d["hidden_truth"] = {"archetype": arch, "p_buy": {k: round(v, 3) for k, v in truth["p_true"].items()}}
    return d


@app.post("/api/checkout/orders", tags=["PayPal"])
def create_order(req: OrderRequest) -> dict:
    try:
        return checkout.create(req.decision_id)
    except KeyError:
        raise HTTPException(404, "decision not found")
    except (ValueError, RuntimeError) as e:
        raise HTTPException(400, str(e))


@app.post("/api/checkout/orders/{order_id}/capture", tags=["PayPal"])
def capture_order(order_id: str, req: CaptureRequest) -> dict:
    try:
        return checkout.capture(order_id, req.funding_source)
    except KeyError:
        raise HTTPException(404, "order not found")
    except RuntimeError as e:
        raise HTTPException(400, str(e))


@app.post("/api/checkout/abandon/{decision_id}", tags=["Demo"])
def abandon(decision_id: str) -> dict:
    d = db.get_decision(decision_id)
    if d and d["outcome"] == "pending":
        db.update_decision(decision_id, outcome="abandoned", realized_profit=0.0)
    return {"ok": True}


# ------------------------------------------------------------------ dashboard
@app.get("/api/decisions", tags=["Dashboard"])
def decisions(limit: int = 500, source: str | None = None) -> list[dict]:
    return db.list_decisions(min(limit, 2000), source)


@app.get("/api/decisions/{decision_id}", tags=["Dashboard"])
def decision(decision_id: str) -> dict:
    d = db.get_decision(decision_id)
    if not d:
        raise HTTPException(404, "not found")
    return d


@app.get("/api/stats", tags=["Dashboard"])
def stats() -> dict:
    ev_path = ARTIFACTS / "eval.json"
    ev = json.loads(ev_path.read_text()) if ev_path.exists() else None
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    spent = db.query("SELECT COALESCE(SUM(expected_spend),0) s, COUNT(*) n FROM decisions WHERE source!='simulated' AND substr(created_at,1,10)=?", (day,))[0]
    mix = db.query("SELECT incentive, COUNT(*) n, SUM(outcome='bought') bought, SUM(outcome!='pending') settled, "
                   "ROUND(SUM(COALESCE(realized_profit,0)),2) profit FROM decisions GROUP BY incentive")
    fair = db.query(
        "SELECT 'mobile' grp, COUNT(*) n, AVG(incentive!='none') offer_rate, AVG(incentive IN ('discount_5','discount_10')) discount_rate FROM decisions WHERE is_mobile=1 "
        "UNION ALL SELECT 'desktop', COUNT(*), AVG(incentive!='none'), AVG(incentive IN ('discount_5','discount_10')) FROM decisions WHERE is_mobile=0 "
        "UNION ALL SELECT 'new visitor', COUNT(*), AVG(incentive!='none'), AVG(incentive IN ('discount_5','discount_10')) FROM decisions WHERE is_returning=0 "
        "UNION ALL SELECT 'returning visitor', COUNT(*), AVG(incentive!='none'), AVG(incentive IN ('discount_5','discount_10')) FROM decisions WHERE is_returning=1")
    paid = db.query("SELECT COUNT(*) n, ROUND(COALESCE(SUM(paypal_fee),0),2) fees FROM decisions WHERE paypal_capture_id IS NOT NULL")[0]
    return {"eval": ev, "budget": {"spent_today": round(spent["s"], 2), "limit": DEFAULT.daily_incentive_budget, "decisions_today": spent["n"]},
            "mix": mix, "fairness": fair, "sandbox_payments": paid, "labels": LABELS}


@app.post("/api/copilot", tags=["Dashboard"])
def copilot_endpoint(req: CopilotRequest) -> dict:
    return copilot.answer(req.question)


# ------------------------------------------------------------------ PayPal webhooks
@app.post("/webhooks/paypal", tags=["PayPal"])
async def paypal_webhook(request: Request) -> JSONResponse:
    event = json.loads(await request.body())
    if not pp.verify_webhook(dict(request.headers), event):
        return JSONResponse({"ok": False, "reason": "signature not verified"}, status_code=400)
    custom_id = pp.custom_id_of(event) or ""
    ours = custom_id.startswith(pp.CUSTOM_ID_PREFIX)
    with db.conn() as c:
        c.execute("INSERT OR IGNORE INTO webhook_events VALUES (?,?,?,?,?,?,?,?)",
                  (event.get("id"), service.now(), event.get("event_type"), (event.get("resource") or {}).get("id"),
                   custom_id if ours else None, 1, int(ours), json.dumps(event) if ours else None))
    if ours and event.get("event_type") == "PAYMENT.CAPTURE.COMPLETED":
        did = custom_id[len(pp.CUSTOM_ID_PREFIX):]
        res = event["resource"]
        d = db.get_decision(did)
        if d and not d.get("paypal_capture_id"):
            fee = float(((res.get("seller_receivable_breakdown") or {}).get("paypal_fee") or {}).get("value", 0) or 0)
            db.update_decision(did, paypal_capture_id=res["id"], paypal_fee=fee, outcome="bought")
    return JSONResponse({"ok": True, "ours": ours})


@app.get("/api/webhook-events", tags=["PayPal"])
def webhook_events(limit: int = 20) -> list[dict]:
    return db.query("SELECT id, received_at, event_type, resource_id, custom_id, verified FROM webhook_events "
                    "WHERE ours=1 ORDER BY received_at DESC LIMIT ?", (min(limit, 200),))


# ------------------------------------------------------------------ pages
app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/", include_in_schema=False)
def page_store():
    return FileResponse(WEB / "index.html")


@app.get("/replay", include_in_schema=False)
def page_replay():
    return FileResponse(WEB / "replay.html")


@app.get("/dashboard", include_in_schema=False)
def page_dashboard():
    return FileResponse(WEB / "dashboard.html")
