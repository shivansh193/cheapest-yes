"""PayPal Orders v2 for a logged decision. Amounts are always rebuilt on the server from the stored
decision and catalog prices; the browser only sends a decision id."""
from __future__ import annotations

import uuid

from cy.config import DEFAULT
from cy.economics import amounts, incentive_cost

from . import catalog, db
from . import paypal_client as pp


def _m(v: float) -> dict:
    return {"currency_code": "USD", "value": f"{v:.2f}"}


def build_order(decision: dict) -> dict:
    inc = decision["incentive"]
    cart = decision["cart"]
    a = amounts(sum(i["price"] * i.get("qty", 1) for i in cart), inc)
    a.check_ceiling(decision["item_total"])
    items = [{"name": i["title"][:120], "sku": i["id"], "quantity": str(i.get("qty", 1)),
              "unit_amount": _m(i["price"]), "category": "PHYSICAL_GOODS"} for i in cart]
    if inc == "addon":
        addon = catalog.catalog().get("addon") or {"id": "addon", "title": DEFAULT.addon_name}
        items.append({"name": f"FREE GIFT: {addon['title'][:100]}", "sku": addon["id"], "quantity": "1",
                      "unit_amount": _m(0.0), "category": "PHYSICAL_GOODS"})
    breakdown = {"item_total": _m(a.item_total), "shipping": _m(a.shipping)}
    if a.discount:
        breakdown["discount"] = _m(a.discount)
    return {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": decision["id"],
            "custom_id": f"{pp.CUSTOM_ID_PREFIX}{decision['id']}",
            "description": "Cheapest Yes demo store (sandbox)",
            "amount": {**_m(a.total), "breakdown": breakdown},
            "items": items,
        }],
    }


def create(decision_id: str) -> dict:
    d = db.get_decision(decision_id)
    if not d:
        raise KeyError(decision_id)
    if d.get("paypal_capture_id"):
        raise ValueError("already paid")
    body = build_order(d)
    r = pp.request("POST", "/v2/checkout/orders", json=body, headers={"PayPal-Request-Id": f"{decision_id}-{uuid.uuid4().hex[:6]}"})
    j = r.json()
    if r.status_code >= 300:
        raise RuntimeError(j.get("message") or str(j)[:300])
    db.update_decision(decision_id, paypal_order_id=j["id"])
    return {"id": j["id"], "status": j["status"], "total": body["purchase_units"][0]["amount"]["value"]}


def capture(order_id: str, funding_source: str | None) -> dict:
    d = db.find_by_order(order_id)
    if not d:
        raise KeyError(order_id)
    r = pp.request("POST", f"/v2/checkout/orders/{order_id}/capture", headers={"PayPal-Request-Id": f"cap-{order_id}"})
    j = r.json()
    if r.status_code >= 300:
        raise RuntimeError(j.get("message") or str(j)[:300])
    cap = j["purchase_units"][0]["payments"]["captures"][0]
    srb = cap.get("seller_receivable_breakdown") or {}
    fee = float((srb.get("paypal_fee") or {}).get("value", 0) or 0)
    item_total = d["item_total"]
    margin = DEFAULT.gross_margin_rate * item_total
    profit = margin - incentive_cost(item_total, d["incentive"]) - fee
    db.update_decision(d["id"], paypal_capture_id=cap["id"], funding_source=funding_source or "paypal",
                       paypal_fee=fee, outcome="bought", realized_profit=round(profit, 2))
    return {"order_id": order_id, "capture_id": cap["id"], "status": cap["status"], "amount": cap["amount"],
            "paypal_fee": fee, "net": (srb.get("net_amount") or {}).get("value"), "decision_id": d["id"],
            "payer": (j.get("payer") or {}).get("name", {}).get("given_name")}
