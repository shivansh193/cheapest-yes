"""Explanations.

1. reasons_for(): TreeSHAP contributions turned into readable reasons. For a chosen incentive
   they explain the *uplift* (logit P(buy|incentive) - logit P(buy|none)); for "none" they
   explain why the shopper is likely to buy anyway, or why nothing pays for itself.
2. template_sentence(): a deterministic one-liner, always available.
3. llm_sentence(): Gemini rewrites the reasons into one plain sentence for the merchant
   dashboard. It never decides anything and is given only the facts below.
"""
from __future__ import annotations

import json
import os
import time

import httpx
import pandas as pd

from .config import LABELS


def _fmt(feature: str, v: float) -> str | None:
    v = float(v)
    if feature == "cart_value":
        return f"the cart is ${v:,.0f}"
    if feature == "hesitation_after_total_s":
        return f"they paused {v:.0f}s after seeing the total" if v >= 1 else "they didn't pause at the total"
    if feature == "hesitation_after_shipping_s":
        return f"they paused {v:.0f}s right after the shipping cost appeared" if v >= 1 else "the shipping cost didn't slow them down"
    if feature == "compare_events":
        return f"{v:.0f} price-comparison signals (copied a product name / switched tabs)" if v else "no price-comparison behaviour"
    if feature == "accessory_views":
        return f"they looked at {v:.0f} accessories" if v else "no interest in accessories"
    if feature == "prior_orders":
        return f"{v:.0f} past order{'s' if v != 1 else ''} with this store" if v else "no past orders"
    if feature == "is_returning":
        return "a returning visitor" if v else "a first-time visitor"
    if feature == "is_mobile":
        return "on mobile" if v else "on desktop"
    if feature == "cart_returns":
        return f"came back to the cart {v:.0f} times" if v else "went straight to checkout"
    if feature == "product_views":
        return f"viewed {v:.0f} product pages"
    if feature == "time_on_page_s":
        return f"spent {v:.0f}s on checkout"
    if feature == "intent_score":
        return f"browsing pattern scores {v:.2f} on the purchase-intent model"
    if feature == "shipping_share":
        return f"shipping would add {v:.0%} to the cart"
    if feature == "n_items":
        return f"{v:.0f} items in the cart"
    return None


def reasons_for(X: pd.DataFrame, incentive: str, model, session: dict, k: int = 3) -> list[dict]:
    if incentive == "none":
        c = model.base_contrib(X).iloc[0]
        direction = 1  # features pushing P(buy) up explain "they'll buy anyway"
    else:
        c = model.uplift_contrib(X, incentive).iloc[0]
        direction = 1
    ranked = sorted(c.items(), key=lambda kv: kv[1] * direction, reverse=True)
    out = []
    for f, s in ranked:
        if s * direction <= 0.02 or len(out) >= k:
            break
        text = _fmt(f, X.iloc[0][f])
        if text:
            out.append({"feature": f, "value": float(X.iloc[0][f]), "contribution": round(float(s), 3), "text": text})
    return out


def template_sentence(incentive: str, reasons: list[dict], best, options, session: dict) -> str:
    why = " and ".join(r["text"] for r in reasons[:2]) if reasons else "the models see no strong signal"
    p = {o.incentive: o.p_buy for o in options}
    if incentive == "none":
        top = max((o for o in options if o.incentive != "none" and o.allowed), key=lambda o: o.gain_vs_none, default=None)
        if p["none"] >= 0.6:
            return (f"No incentive: likely to buy anyway (P(buy) {p['none']:.0%}) because {why}, "
                    f"so any offer would mostly give margin away.")
        if top is None:
            return "No incentive: every paid option is blocked by a guardrail."
        return (f"No incentive: the best option ({LABELS[top.incentive]}) would change expected profit by "
                f"${top.gain_vs_none:+.2f}, which doesn't pay for itself.")
    return (f"{LABELS[incentive]} because {why}. P(buy) {p['none']:.0%} -> {p[incentive]:.0%}; "
            f"expected profit {best.gain_vs_none:+.2f} USD vs no incentive.")


def llm_sentence(decision: dict, timeout: float = 20.0) -> str | None:
    """One plain-English sentence for the merchant. Returns None on any failure (the template is the fallback)."""
    facts = {
        "chosen_incentive": decision["label"],
        "reasons": [r["text"] for r in decision["reasons"]],
        "p_buy": {o["incentive"]: o["p_buy"] for o in decision["options"]},
        "expected_profit_gain_usd": decision["expected_gain"],
        "guardrails_hit": decision["guardrails"],
    }
    prompt = (
        "You write one sentence (max 35 words) for an online merchant's dashboard explaining why their "
        "checkout showed a shopper this incentive. Use only these facts; no new numbers, no hype, "
        "no second sentence. Call the person 'the shopper'. If the incentive is 'No incentive', explain why "
        "nothing was offered. Reply with the sentence only.\n"
        + json.dumps(facts)
    )
    from .llm import generate

    text, _ = generate(prompt, max_tokens=400, timeout=timeout)
    return text.strip().split("\n")[0][:400] if text else None
