"""Shared helpers for spike scripts. Never prints secrets."""
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PAYPAL_BASE = os.environ.get("PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")
if "sandbox" not in PAYPAL_BASE:
    raise SystemExit("Refusing to run: PAYPAL_API_BASE is not a sandbox URL.")


def paypal_token() -> str:
    r = httpx.post(
        f"{PAYPAL_BASE}/v1/oauth2/token",
        auth=(os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_CLIENT_SECRET"]),
        data={"grant_type": "client_credentials"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def paypal(method: str, path: str, token: str, **kw) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    headers.update(kw.pop("headers", {}))
    return httpx.request(method, f"{PAYPAL_BASE}{path}", headers=headers, timeout=30, **kw)
