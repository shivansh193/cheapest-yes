"""Demo-store catalog from the Channel3 product API (https://trychannel3.com)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

SNAPSHOT = Path(__file__).resolve().parent.parent / "artifacts" / "catalog.json"
API = "https://api.trychannel3.com/v1/search"
QUERIES = [
    ("Headphones", "noise cancelling over-ear headphones", 3),
    ("Earbuds", "wireless earbuds", 2),
    ("Speakers", "portable bluetooth speaker", 2),
    ("Keyboards", "mechanical keyboard", 2),
    ("Watches", "smartwatch", 2),
    ("Accessories", "usb-c hub", 1),
    ("Accessories", "laptop stand", 1),
]
ADDON_QUERY = "headphone carrying case"


def _norm(p: dict, category: str) -> dict | None:
    offers = [o for o in p.get("offers") or [] if (o.get("price") or {}).get("currency") == "USD" and (o.get("price") or {}).get("price")]
    imgs = p.get("images") or []
    if not offers or not imgs:
        return None
    img = next((i for i in imgs if i.get("is_main_image")), imgs[0])
    brand = ((p.get("brands") or [{}])[0] or {}).get("name") or ""
    return {
        "id": p["id"],
        "title": p["title"],
        "brand": brand,
        "category": category,
        "price": round(float(min(o["price"]["price"] for o in offers)), 2),
        "image": img.get("cleaned_url") or img.get("url"),
        "description": (p.get("description") or "")[:400],
        "features": (p.get("key_features") or [])[:4],
        "source": "Channel3",
    }


def _search(q: str, key: str) -> list[dict]:
    r = httpx.post(API, headers={"x-api-key": key}, json={"query": q}, timeout=60)
    r.raise_for_status()
    d = r.json()
    return d.get("products", d) if isinstance(d, dict) else d


def fetch() -> dict:
    key = os.environ["CHANNEL3_API_KEY"]
    seen, products = set(), []
    for category, q, k in QUERIES:
        got = 0
        for p in _search(q, key):
            n = _norm(p, category)
            if n and n["id"] not in seen and (n["brand"], category) not in seen and 15 <= n["price"] <= 600:
                seen.update({n["id"], (n["brand"], category)})
                products.append(n)
                got += 1
            if got >= k:
                break
    addon = next((n for n in (_norm(p, "Add-on") for p in _search(ADDON_QUERY, key)) if n and n["price"] <= 40), None)
    return {"products": products, "addon": addon}


_CACHE: dict | None = None


def catalog(refresh: bool = False) -> dict:
    global _CACHE
    if refresh and os.environ.get("CHANNEL3_API_KEY"):
        try:
            _CACHE = fetch()
            return _CACHE
        except Exception:  # noqa: BLE001
            pass
    if _CACHE is None:
        _CACHE = json.loads(SNAPSHOT.read_text())
    return _CACHE


def by_id() -> dict[str, dict]:
    return {p["id"]: p for p in catalog()["products"]}
