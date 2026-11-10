"""SQLite storage for decisions, orders and webhook events."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", "cheapest_yes.db"))
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  source TEXT NOT NULL,              -- 'simulated' | 'store' | 'replay' | 'api'
  persona TEXT,
  shopper_key TEXT,
  is_mobile INTEGER, is_returning INTEGER,
  cart_json TEXT, session_json TEXT,
  item_total REAL,
  incentive TEXT NOT NULL,
  options_json TEXT,
  expected_gain REAL,
  expected_spend REAL,
  amounts_json TEXT,
  reasons_json TEXT,
  explanation TEXT,
  llm_explanation TEXT,
  guardrails_json TEXT,
  paypal_order_id TEXT,
  paypal_capture_id TEXT,
  funding_source TEXT,
  paypal_fee REAL,
  outcome TEXT DEFAULT 'pending',    -- 'pending' | 'bought' | 'abandoned'
  realized_profit REAL
);
CREATE INDEX IF NOT EXISTS ix_dec_created ON decisions(created_at);
CREATE INDEX IF NOT EXISTS ix_dec_order ON decisions(paypal_order_id);
CREATE TABLE IF NOT EXISTS webhook_events (
  id TEXT PRIMARY KEY, received_at TEXT, event_type TEXT, resource_id TEXT,
  custom_id TEXT, verified INTEGER, ours INTEGER, payload TEXT
);
"""


@contextmanager
def conn():
    with _lock:
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)


def insert_decision(row: dict) -> None:
    cols = ",".join(row)
    q = ",".join("?" for _ in row)
    vals = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in row.values()]
    with conn() as c:
        c.execute(f"INSERT INTO decisions ({cols}) VALUES ({q})", vals)


def update_decision(decision_id: str, **fields) -> None:
    if not fields:
        return
    sets = ",".join(f"{k}=?" for k in fields)
    vals = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in fields.values()]
    with conn() as c:
        c.execute(f"UPDATE decisions SET {sets} WHERE id=?", [*vals, decision_id])


def get_decision(decision_id: str) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
    return _row(r) if r else None


def find_by_order(order_id: str) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM decisions WHERE paypal_order_id=?", (order_id,)).fetchone()
    return _row(r) if r else None


def list_decisions(limit: int = 500, source: str | None = None) -> list[dict]:
    q = "SELECT * FROM decisions"
    args: list = []
    if source:
        q += " WHERE source=?"
        args.append(source)
    q += " ORDER BY created_at DESC LIMIT ?"
    args.append(limit)
    with conn() as c:
        return [_row(r) for r in c.execute(q, args).fetchall()]


def query(sql: str, args: tuple = ()) -> list[dict]:
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in list(d):
        if k.endswith("_json") and d[k]:
            d[k[:-5]] = json.loads(d.pop(k))
        elif k.endswith("_json"):
            d[k[:-5]] = None
            d.pop(k)
    return d
