"""PayPal sandbox client: OAuth token cache, Orders v2 helpers, webhook signature verification."""
from __future__ import annotations

import os
import time

import httpx

API_BASE = os.environ.get("PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")
if "sandbox" not in API_BASE:
    raise RuntimeError("Cheapest Yes only runs against the PayPal sandbox.")

# Orders created by this app carry this prefix in custom_id. The sandbox app is
# shared with other projects, so webhook events without it are ignored.
CUSTOM_ID_PREFIX = "cheapest-yes:"

_token: dict = {"value": None, "exp": 0.0}


def token() -> str:
    if _token["value"] and time.time() < _token["exp"] - 60:
        return _token["value"]
    r = httpx.post(
        f"{API_BASE}/v1/oauth2/token",
        auth=(os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_CLIENT_SECRET"]),
        data={"grant_type": "client_credentials"},
        timeout=30,
    )
    r.raise_for_status()
    d = r.json()
    _token.update(value=d["access_token"], exp=time.time() + d["expires_in"])
    return d["access_token"]


def request(method: str, path: str, **kw) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token()}", "Content-Type": "application/json"}
    headers.update(kw.pop("headers", {}))
    return httpx.request(method, f"{API_BASE}{path}", headers=headers, timeout=30, **kw)


def verify_webhook(headers: dict[str, str], raw_event: dict) -> bool:
    """Ask PayPal to verify the transmission signature. Returns True only on SUCCESS."""
    webhook_id = os.environ.get("PAYPAL_WEBHOOK_ID")
    if not webhook_id:
        return False
    h = {k.lower(): v for k, v in headers.items()}
    body = {
        "auth_algo": h.get("paypal-auth-algo"),
        "cert_url": h.get("paypal-cert-url"),
        "transmission_id": h.get("paypal-transmission-id"),
        "transmission_sig": h.get("paypal-transmission-sig"),
        "transmission_time": h.get("paypal-transmission-time"),
        "webhook_id": webhook_id,
        "webhook_event": raw_event,
    }
    if not all(body.values()):
        return False
    r = request("POST", "/v1/notifications/verify-webhook-signature", json=body)
    return r.status_code == 200 and r.json().get("verification_status") == "SUCCESS"


def custom_id_of(event: dict) -> str | None:
    res = event.get("resource") or {}
    if "custom_id" in res:
        return res["custom_id"]
    for pu in res.get("purchase_units") or []:
        if pu.get("custom_id"):
            return pu["custom_id"]
    return None
