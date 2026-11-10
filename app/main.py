"""Cheapest Yes API. This first cut only carries the PayPal webhook receiver used by spike 3."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import paypal_client as pp

DB_PATH = Path(os.environ.get("DB_PATH", "cheapest_yes.db"))

app = FastAPI(title="Cheapest Yes", version="0.1.0")


def db() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.execute(
        """CREATE TABLE IF NOT EXISTS webhook_events (
            id TEXT PRIMARY KEY, received_at TEXT, event_type TEXT, resource_id TEXT,
            custom_id TEXT, verified INTEGER, ours INTEGER, payload TEXT)"""
    )
    return c


@app.get("/health")
def health() -> dict:
    return {"ok": True, "paypal": pp.API_BASE, "webhook_configured": bool(os.environ.get("PAYPAL_WEBHOOK_ID"))}


@app.post("/webhooks/paypal")
async def paypal_webhook(request: Request) -> JSONResponse:
    event = json.loads(await request.body())
    verified = pp.verify_webhook(dict(request.headers), event)
    if not verified:
        return JSONResponse({"ok": False, "reason": "signature not verified"}, status_code=400)
    custom_id = pp.custom_id_of(event) or ""
    ours = custom_id.startswith(pp.CUSTOM_ID_PREFIX)
    with db() as c:
        c.execute(
            "INSERT OR IGNORE INTO webhook_events VALUES (?,?,?,?,?,?,?,?)",
            (
                event.get("id"),
                datetime.now(timezone.utc).isoformat(),
                event.get("event_type"),
                (event.get("resource") or {}).get("id"),
                custom_id if ours else None,
                1,
                int(ours),
                # Events from other projects sharing the sandbox app are counted, not stored.
                json.dumps(event) if ours else None,
            ),
        )
    return JSONResponse({"ok": True, "ours": ours})


@app.get("/api/webhook-events")
def webhook_events(limit: int = 20) -> list[dict]:
    with db() as c:
        rows = c.execute(
            "SELECT id, received_at, event_type, resource_id, custom_id, verified FROM webhook_events "
            "WHERE ours = 1 ORDER BY received_at DESC LIMIT ?",
            (min(limit, 200),),
        ).fetchall()
    keys = ["id", "received_at", "event_type", "resource_id", "custom_id", "verified"]
    return [dict(zip(keys, r)) for r in rows]
