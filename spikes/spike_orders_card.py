"""Spike 1b: same breakdown as spike_orders.py, paid server-side with a published
sandbox test card so create -> capture runs without a buyer login.
Sandbox only (common.py refuses non-sandbox URLs)."""
import json
import uuid

from common import paypal, paypal_token
from spike_orders import discount, item_total, items, m, shipping, total

TEST_CARD = {"number": "4111111111111111", "expiry": "2030-12", "security_code": "123", "name": "Test Buyer",
             "billing_address": {"address_line_1": "1 Main St", "admin_area_2": "San Jose", "admin_area_1": "CA",
                                 "postal_code": "95131", "country_code": "US"}}

t = paypal_token()
body = {
    "intent": "CAPTURE",
    "purchase_units": [{
        "reference_id": "spike-1b",
        "amount": {**m(total), "breakdown": {"item_total": m(item_total), "shipping": m(shipping), "discount": m(discount)}},
        "items": [{"name": i["name"], "quantity": str(i["quantity"]), "unit_amount": m(i["unit_amount"])} for i in items],
    }],
    "payment_source": {"card": TEST_CARD},
}
r = paypal("POST", "/v2/checkout/orders", t, json=body, headers={"PayPal-Request-Id": str(uuid.uuid4())})
d = r.json()
print("create status", r.status_code, d.get("id"), d.get("status"))
for pu in d.get("purchase_units", []):
    print("amount", json.dumps(pu.get("amount")))
    for c in pu.get("payments", {}).get("captures", []):
        print("capture", c["id"], c["status"], c["amount"])
        print("seller_receivable", json.dumps(c.get("seller_receivable_breakdown")))
if r.status_code >= 300:
    print(json.dumps(d, indent=1)[:1500])
