"""Glue between HTTP and the engine: build features, apply guardrail state, log decisions."""
from __future__ import annotations

import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from cy import sim
from cy.config import DEFAULT
from cy.data import load_uci
from cy.economics import amounts, profit_if_buy
from cy.engine import decide
from cy.explain import llm_sentence
from cy.features import FEATURE_ORDER, UCI_FEATURES
from cy.models import get_bundle, uci_frame

from . import catalog, db

_pool = ThreadPoolExecutor(max_workers=2)
_UCI_MED: dict | None = None


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def shopper_hash(raw: str | None) -> str | None:
    return hashlib.sha256(raw.encode()).hexdigest()[:16] if raw else None


def _uci_medians() -> dict:
    global _UCI_MED
    if _UCI_MED is None:
        _UCI_MED = uci_frame(load_uci()).median().to_dict()
    return _UCI_MED


def intent_from_session(s: dict) -> float:
    """Live store sessions don't have every UCI field. Map what we observe (product pages and time,
    returning visitor) and fill the rest with dataset medians."""
    row = dict(_uci_medians())
    row["ProductRelated"] = float(s.get("product_views") or row["ProductRelated"])
    row["ProductRelated_Duration"] = float(s.get("browse_seconds") or 30 * row["ProductRelated"])
    row["is_returning"] = float(s.get("is_returning", 0))
    row["is_weekend"] = float(datetime.now().weekday() >= 5)
    if s.get("page_values") is not None:
        row["PageValues"] = float(s["page_values"])
    X = pd.DataFrame([row])[UCI_FEATURES]
    return float(np.round(get_bundle().intent.predict(X)[0], 4))


def guardrail_state(shopper_key: str | None) -> tuple[float, int]:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    spent = db.query("SELECT COALESCE(SUM(expected_spend),0) s FROM decisions WHERE source != 'simulated' AND substr(created_at,1,10)=?", (day,))[0]["s"]
    n = 0
    if shopper_key:
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        n = db.query("SELECT COUNT(*) n FROM decisions WHERE shopper_key=? AND incentive NOT IN ('none','paylater') AND created_at>=?",
                     (shopper_key, since))[0]["n"]
    return float(spent), int(n)


def run_decision(cart: list[dict], session: dict, source: str, shopper_id: str | None = None,
                 persona: str | None = None, created_at: str | None = None, llm: bool = True,
                 budget_override: tuple[float, int] | None = None) -> dict:
    item_total = round(sum(float(i["price"]) * int(i.get("qty", 1)) for i in cart), 2)
    s = {**session, "cart_value": item_total, "n_items": sum(int(i.get("qty", 1)) for i in cart)}
    if s.get("intent_score") is None:
        s["intent_score"] = intent_from_session(s)
    key = shopper_hash(shopper_id)
    spent, n7 = budget_override or guardrail_state(key)
    d = decide(s, get_bundle().response, DEFAULT, budget_spent_today=spent, shopper_incentives_7d=n7)
    chosen = next(o for o in d.options if o.incentive == d.incentive)
    did = "dec_" + uuid.uuid4().hex[:12]
    db.insert_decision({
        "id": did, "created_at": created_at or now(), "source": source, "persona": persona, "shopper_key": key,
        "is_mobile": int(s.get("is_mobile", 0)), "is_returning": int(s.get("is_returning", 0)),
        "cart_json": cart, "session_json": {k: s.get(k) for k in FEATURE_ORDER},
        "item_total": item_total, "incentive": d.incentive,
        "options_json": [o.__dict__ for o in d.options], "expected_gain": d.expected_gain,
        "expected_spend": chosen.expected_spend, "amounts_json": d.amounts, "reasons_json": d.reasons,
        "explanation": d.explanation, "guardrails_json": d.guardrails,
    })
    out = d.to_dict()
    out.update(decision_id=did, session={k: s.get(k) for k in FEATURE_ORDER}, cart=cart, created_at=created_at or now())
    if llm:
        _pool.submit(_llm_job, did, out)
    return out


def _llm_job(did: str, decision: dict) -> None:
    text = llm_sentence(decision)
    if text:
        db.update_decision(did, llm_explanation=text)


# ------------------------------------------------------------------ replay + seeding
def cart_for_value(target: float, rng: np.random.Generator) -> list[dict]:
    """Pick real catalog products whose total lands near a simulated cart value."""
    prods = sorted(catalog.catalog()["products"], key=lambda p: p["price"])
    cart, total = [], 0.0
    for _ in range(3):
        remaining = target - total
        if remaining < 15 and cart:
            break
        fits = [p for p in prods if p["price"] <= remaining * 1.15 and p["id"] not in {c["id"] for c in cart}]
        pick = max(fits, key=lambda p: p["price"]) if fits else (prods[0] if not cart else None)
        if pick is None:
            break
        if fits and len(fits) > 1 and rng.random() < 0.4:
            pick = fits[-2]
        cart.append({"id": pick["id"], "title": pick["title"], "brand": pick["brand"], "price": pick["price"], "image": pick["image"], "qty": 1})
        total += pick["price"]
    return cart


def simulated_shopper(persona_archetype: str | None, seed: int, typical: bool = False) -> tuple[dict, str, dict]:
    """One simulated shopper. With typical=True (replay mode), draw 15 members of the persona and keep
    the one whose hidden response profile is closest to the persona's average, so the replay shows a
    representative shopper. The engine still only sees session signals."""
    from cy.config import INCENTIVES
    from cy.train import with_intent

    b = get_bundle()
    n = 25 if typical and persona_archetype else 1
    pop = sim.generate(n, load_uci(), seed=seed, archetype=persona_archetype)
    X = with_intent(pop, b.intent)
    i = 0
    if n > 1:
        # medoid: close to the persona's hidden profile AND to the median of its visible signals
        a = sim.ARCHETYPES[persona_archetype]
        target = np.array([a["p0"]] + [a["p0"] + a["lift"][k] for k in INCENTIVES[1:]])
        truth_d = np.abs(pop.p_true.to_numpy() - target).sum(axis=1)
        cols = ["cart_value", "hesitation_after_shipping_s", "hesitation_after_total_s", "compare_events", "product_views",
                "accessory_views", "cart_returns", "prior_orders", "intent_score"]
        Z = X[cols].astype(float)
        Z["cart_value"] = np.log(Z["cart_value"])
        Z = (Z - Z.median()) / (Z.std() + 1e-6)
        sig_d = Z.abs().mean(axis=1).to_numpy()
        i = int((truth_d * 4 + sig_d).argmin())
    return X.iloc[i].to_dict(), pop.archetype[i], {"p_true": pop.p_true.iloc[i].to_dict(), "pl_true": pop.pl_true.iloc[i].to_dict(),
                                                   "uci": pop.uci.iloc[i][["ProductRelated", "ProductRelated_Duration", "BounceRates", "ExitRates", "PageValues", "VisitorType"]].to_dict()}


def seed_simulated(n: int = 360) -> int:
    """Fill the decision log with simulated shoppers so the dashboard isn't empty on a fresh deploy.
    Outcomes come from the simulator's hidden truth. Clearly marked source='simulated'."""
    have = db.query("SELECT COUNT(*) n FROM decisions WHERE source='simulated'")[0]["n"]
    if have:
        return 0
    rng = np.random.default_rng(42)
    start = datetime.now(timezone.utc) - timedelta(hours=36)
    for i in range(n):
        s, arch, truth = simulated_shopper(None, seed=10_000 + i)
        cart = cart_for_value(s["cart_value"], rng)
        ts = (start + timedelta(minutes=float(i) * 36 * 60 / n + float(rng.uniform(0, 5)))).isoformat(timespec="seconds")
        d = run_decision(cart, s, "simulated", shopper_id=f"sim-{i}", persona=arch, created_at=ts, llm=False, budget_override=(0.0, 0))
        inc = d["incentive"]
        bought = rng.random() < truth["p_true"][inc]
        used_pl = bought and rng.random() < truth["pl_true"][inc]
        a = amounts(d["amounts"]["item_total"], inc)
        profit = profit_if_buy(a.item_total, inc, 1.0 if used_pl else 0.0) if bought else 0.0
        db.update_decision(d["decision_id"], outcome="bought" if bought else "abandoned",
                           funding_source=("paylater" if used_pl else "paypal") if bought else None,
                           realized_profit=round(profit, 2))
    return n
