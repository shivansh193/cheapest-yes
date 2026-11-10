"""Build artifacts/catalog.json from the Channel3 product API.

    python scripts/fetch_catalog.py

Real products, prices and images (hosted on Channel3's CDN). The app serves this snapshot so the
demo store works even if the API is slow; /api/products?refresh=1 re-fetches live.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.catalog import QUERIES, ADDON_QUERY, fetch  # noqa: E402

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    if not os.environ.get("CHANNEL3_API_KEY"):
        sys.exit("CHANNEL3_API_KEY not set")
    cat = fetch()
    (ROOT / "artifacts" / "catalog.json").write_text(json.dumps(cat, indent=1))
    print(f"{len(cat['products'])} products, add-on: {cat['addon']['title'] if cat['addon'] else None}")
    for p in cat["products"]:
        print(f"  ${p['price']:>8.2f}  {p['brand']:<14} {p['title'][:60]}")
