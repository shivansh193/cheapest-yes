"""Spike 4: Channel3 returns real products with prices and images."""
import json
import os
import sys

import httpx

import common  # noqa: F401  (loads .env)

query = sys.argv[1] if len(sys.argv) > 1 else "wireless headphones"
r = httpx.post(
    "https://api.trychannel3.com/v1/search",
    headers={"x-api-key": os.environ["CHANNEL3_API_KEY"], "Content-Type": "application/json"},
    json={"query": query},
    timeout=60,
)
print("status", r.status_code)
data = r.json()
items = data if isinstance(data, list) else data.get("products") or data.get("results") or data
if isinstance(items, list):
    print("count", len(items))
    print("keys", sorted(items[0].keys()) if items else None)
    for p in items[:5]:
        print(json.dumps(p, default=str)[:600])
else:
    print(json.dumps(data, default=str)[:1500])
