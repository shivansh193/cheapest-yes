"""Spike 1: Orders v2 order with a discount and $0 shipping in amount.breakdown.

  python spike_orders.py create        -> creates order, prints approve link
  python spike_orders.py capture <id>  -> captures an approved order
"""
import json
import sys
import uuid
from decimal import Decimal

from common import paypal, paypal_token

items = [
    {"name": "Demo headphones", "unit_amount": Decimal("200.00"), "quantity": 1},
    {"name": "Demo cable (add-on, free)", "unit_amount": Decimal("0.00"), "quantity": 1},
]
item_total = sum(i["unit_amount"] * i["quantity"] for i in items)
discount = (item_total * Decimal("0.05")).quantize(Decimal("0.01"))
shipping = Decimal("0.00")
total = item_total + shipping - discount


def m(v: Decimal) -> dict:
    return {"currency_code": "USD", "value": f"{v:.2f}"}


def create(token: str) -> None:
    body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": "spike-1",
            "amount": {
                **m(total),
                "breakdown": {"item_total": m(item_total), "shipping": m(shipping), "discount": m(discount)},
            },
            "items": [{"name": i["name"], "quantity": str(i["quantity"]), "unit_amount": m(i["unit_amount"])} for i in items],
        }],
        "payment_source": {"paypal": {"experience_context": {
            "user_action": "PAY_NOW", "shipping_preference": "NO_SHIPPING",
            "return_url": "https://example.com/return", "cancel_url": "https://example.com/cancel"}}},
    }
    r = paypal("POST", "/v2/checkout/orders", token, json=body, headers={"PayPal-Request-Id": str(uuid.uuid4())})
    print("status", r.status_code)
    d = r.json()
    print("order", d.get("id"), d.get("status"))
    print("breakdown sent: item_total", item_total, "shipping", shipping, "discount", discount, "total", total)
    for link in d.get("links", []):
        if link["rel"] in ("approve", "payer-action"):
            print("APPROVE:", link["href"])
    if r.status_code >= 300:
        print(json.dumps(d, indent=1)[:2000])


def capture(token: str, order_id: str) -> None:
    r = paypal("POST", f"/v2/checkout/orders/{order_id}/capture", token, headers={"PayPal-Request-Id": str(uuid.uuid4())})
    d = r.json()
    print("status", r.status_code, d.get("status"))
    for pu in d.get("purchase_units", []):
        for c in pu.get("payments", {}).get("captures", []):
            print("capture", c["id"], c["status"], c["amount"])
            print("seller_receivable", json.dumps(c.get("seller_receivable_breakdown")))
    if r.status_code >= 300:
        print(json.dumps(d, indent=1)[:2000])


if __name__ == "__main__":
    t = paypal_token()
    print("token ok")
    if sys.argv[1] == "create":
        create(t)
    else:
        capture(t, sys.argv[2])
