"""Write the public /decide API as an OpenAPI 3 spec (openapi/cheapest-yes.json) for APIMatic.

Only the merchant-facing endpoint is exported; demo-store and dashboard routes stay internal."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.openapi.utils import get_openapi  # noqa: E402

from app.main import app  # noqa: E402

routes = [r for r in app.routes if getattr(r, "path", None) in ("/decide", "/health")]
spec = get_openapi(title="Cheapest Yes API", version=app.version, description=app.description, routes=routes,
                   servers=[{"url": "https://cheapest-yes.onrender.com", "description": "Hosted demo (PayPal sandbox)"}])
spec["info"]["license"] = {"name": "MIT", "url": "https://opensource.org/licenses/MIT"}


def strip_titles(node, top=True):
    """Pydantic puts a 'title' on every property; APIMatic flags duplicates. Keep only schema-level titles."""
    if isinstance(node, dict):
        if not top:
            node.pop("title", None)
        for v in node.values():
            strip_titles(v, top=False)
    elif isinstance(node, list):
        for v in node:
            strip_titles(v, top=False)


def nullable(prop: dict) -> None:
    """anyOf [X, null] -> X with type [X.type, 'null'] (OpenAPI 3.1), which SDK generators map to Optional."""
    any_of = prop.get("anyOf")
    if isinstance(any_of, list) and len(any_of) == 2 and {"type": "null"} in any_of:
        other = next(a for a in any_of if a != {"type": "null"})
        if "type" in other and isinstance(other["type"], str):
            prop.pop("anyOf")
            prop.update(other)
            prop["type"] = [other["type"], "null"]


for name, schema in spec["components"]["schemas"].items():
    for prop in (schema.get("properties") or {}).values():
        strip_titles(prop, top=False)
        nullable(prop)
    schema.setdefault("description", {"HTTPValidationError": "Request failed validation.",
                                      "ValidationError": "One validation problem."}.get(name, name))
    for pname, prop in (schema.get("properties") or {}).items():
        prop.setdefault("description", pname.replace("_", " "))

EXAMPLE_REQ = {"cart": [{"id": "sku-123", "title": "Wireless headphones", "price": 240.0, "qty": 1}],
               "session": {"time_on_page_s": 75, "product_views": 6, "cart_returns": 2, "compare_events": 0,
                           "hesitation_after_shipping_s": 4, "hesitation_after_total_s": 38, "accessory_views": 0,
                           "is_mobile": 1, "is_returning": 0, "prior_orders": 0},
               "shopper_id": "shopper-42"}
EXAMPLE_RES = {"decision_id": "dec_0123456789ab", "incentive": "paylater", "label": "PayPal Pay Later",
               "amounts": {"item_total": 240.0, "shipping": 8.99, "discount": 0.0, "total": 248.99}, "expected_gain": 41.2,
               "explanation": "PayPal Pay Later because the cart is $240 and they paused 38s after seeing the total.",
               "reasons": [{"feature": "cart_value", "value": 240.0, "contribution": 0.61, "text": "the cart is $240"}],
               "options": [], "guardrails": []}
op = spec["paths"]["/decide"]["post"]
op["requestBody"]["description"] = "The cart (list prices) and session-behaviour signals."
op["requestBody"]["content"]["application/json"]["example"] = EXAMPLE_REQ
op["responses"]["200"]["content"]["application/json"]["example"] = EXAMPLE_RES
op["responses"]["422"]["content"]["application/json"]["example"] = {"detail": [{"loc": ["body", "cart"], "msg": "Field required", "type": "missing"}]}
h = spec["paths"]["/health"]["get"]
h["summary"] = "Service health"
h["description"] = "Liveness check; reports the PayPal environment (always sandbox) and model metadata."
h["responses"]["200"]["content"]["application/json"]["example"] = {"ok": True, "paypal": "https://api-m.sandbox.paypal.com"}
out = ROOT / "openapi" / "cheapest-yes.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(spec, indent=2))
print(f"wrote {out.relative_to(ROOT)} with paths: {list(spec['paths'])}")
