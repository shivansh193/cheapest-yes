"""Merchant copilot: answers questions about logged decisions.

The LLM sees only aggregates computed here with SQL (counts, rates, top reasons), never raw
session rows, and is told to answer only from them."""
from __future__ import annotations

import json
import os
from collections import Counter

import httpx

from cy.config import DEFAULT, LABELS

from . import db


def facts() -> dict:
    by_day = db.query(
        "SELECT substr(created_at,1,10) day, incentive, COUNT(*) n, SUM(outcome='bought') bought, "
        "ROUND(SUM(COALESCE(realized_profit,0)),2) profit FROM decisions GROUP BY day, incentive ORDER BY day")
    totals = db.query("SELECT substr(created_at,1,10) day, COUNT(*) n FROM decisions GROUP BY day")
    tot = {r["day"]: r["n"] for r in totals}
    days = {}
    for r in by_day:
        days.setdefault(r["day"], {"shoppers": tot[r["day"]], "by_incentive": {}})["by_incentive"][LABELS[r["incentive"]]] = {
            "count": r["n"], "share": round(r["n"] / tot[r["day"]], 3), "bought": r["bought"], "realized_profit_usd": r["profit"]}
    reasons: dict[str, Counter] = {}
    for r in db.query("SELECT incentive, reasons_json FROM decisions"):
        for x in json.loads(r["reasons_json"] or "[]")[:2]:
            reasons.setdefault(LABELS[r["incentive"]], Counter())[x["feature"]] += 1
    fair = db.query(
        "SELECT CASE is_mobile WHEN 1 THEN 'mobile' ELSE 'desktop' END grp, COUNT(*) n, ROUND(AVG(incentive!='none'),3) offer_rate, "
        "ROUND(AVG(incentive IN ('discount_5','discount_10')),3) discount_rate FROM decisions GROUP BY grp "
        "UNION ALL SELECT CASE is_returning WHEN 1 THEN 'returning' ELSE 'new' END, COUNT(*), ROUND(AVG(incentive!='none'),3), "
        "ROUND(AVG(incentive IN ('discount_5','discount_10')),3) FROM decisions GROUP BY 1")
    sources = db.query("SELECT source, COUNT(*) n FROM decisions GROUP BY source")
    cart = db.query("SELECT incentive, ROUND(AVG(item_total),2) avg_cart, ROUND(AVG(expected_gain),2) avg_expected_gain FROM decisions GROUP BY incentive")
    return {
        "note": "Rows with source 'simulated' are synthetic shoppers seeded for the demo; 'store'/'replay' are sandbox sessions.",
        "by_day": days,
        "top_reason_features_by_incentive": {k: dict(v.most_common(4)) for k, v in reasons.items()},
        "avg_cart_and_expected_gain_by_incentive": {LABELS[r["incentive"]]: {"avg_cart_usd": r["avg_cart"], "avg_expected_gain_usd": r["avg_expected_gain"]} for r in cart},
        "fairness": fair,
        "sources": {r["source"]: r["n"] for r in sources},
        "merchant_config": {"max_discount_pct": DEFAULT.max_discount_pct, "daily_budget_usd": DEFAULT.daily_incentive_budget,
                            "shipping_fee_usd": DEFAULT.shipping_fee, "paylater_extra_fee_pct": DEFAULT.paylater_extra_pct},
    }


def answer(question: str) -> dict:
    f = facts()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return {"answer": "The copilot needs GEMINI_API_KEY. Here are the facts it would use.", "facts": f, "model": None}
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    prompt = (
        "You are the analytics copilot for a merchant using Cheapest Yes, which picks the cheapest checkout incentive "
        "(PayPal Pay Later messaging, free shipping, a free add-on, or a small discount) per shopper to maximise expected "
        "profit, and never raises prices. Answer the merchant's question in 2-4 short sentences using ONLY the JSON facts. "
        "Quote the relevant numbers. Feature names map to: hesitation_after_shipping_s = paused after shipping cost shown; "
        "hesitation_after_total_s = paused after total shown; compare_events = price comparison; cart_value = cart size; "
        "accessory_views = looked at accessories; intent_score = purchase-intent model score. If the facts can't answer it, "
        "say what's missing. No markdown headings.\n\nQUESTION: " + question[:500] + "\n\nFACTS: " + json.dumps(f)
    )
    from cy.llm import generate

    text, used = generate(prompt, max_tokens=1200, timeout=45)
    if text:
        return {"answer": text, "model": used}
    return {"answer": "The AI model didn't respond (free-tier quota or high demand). Try again in a moment.", "model": None}
