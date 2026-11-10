"""Synthetic shopper simulator for the demo store.

Each shopper has a hidden archetype and a hidden, ground-truth purchase probability under
every incentive. The engine never sees those; it only sees session signals. That lets the eval
score policies on *true* expected profit, which no field A/B test can give you.

Grounding in real data: each shopper's browsing behaviour (pages, durations, bounce/exit rates,
page values) is a real session sampled from the UCI Online Shoppers Purchasing Intention dataset
(CC BY 4.0). Cart, hesitation and comparison signals and all incentive responses are simulated.
These are simulator results, not field results.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import INCENTIVES
from .economics import paylater_eligible

# Hidden truth per archetype.
#   p0: P(buy | no incentive)
#   lift: absolute increase in P(buy) per incentive (before per-shopper noise)
#   pl_use: P(pays with Pay Later | buys) without / with prominent Pay Later messaging
ARCHETYPES: dict[str, dict] = {
    "will_buy_anyway": dict(share=0.25, p0=0.82, lift=dict(paylater=.02, free_shipping=.03, addon=.02, discount_5=.04, discount_10=.06), pl_use=(.04, .07)),
    "split_payment":   dict(share=0.15, p0=0.22, lift=dict(paylater=.32, free_shipping=.04, addon=.03, discount_5=.06, discount_10=.12), pl_use=(.15, .78)),
    "shipping_hunter": dict(share=0.15, p0=0.28, lift=dict(paylater=.02, free_shipping=.34, addon=.05, discount_5=.08, discount_10=.15), pl_use=(.04, .08)),
    "price_sensitive": dict(share=0.15, p0=0.18, lift=dict(paylater=.05, free_shipping=.07, addon=.08, discount_5=.15, discount_10=.33), pl_use=(.08, .22)),
    "bundle_seeker":   dict(share=0.10, p0=0.30, lift=dict(paylater=.03, free_shipping=.06, addon=.29, discount_5=.10, discount_10=.17), pl_use=(.05, .10)),
    "browser":         dict(share=0.20, p0=0.03, lift=dict(paylater=.01, free_shipping=.01, addon=.01, discount_5=.02, discount_10=.04), pl_use=(.03, .05)),
}

# Signal distributions per archetype (deliberately overlapping, so the job is not trivial).
#   cart: lognormal (median $), hes_ship/hes_total: mean idle seconds, compare/views/acc/returns: Poisson means
SIGNALS: dict[str, dict] = {
    "will_buy_anyway": dict(cart=110, hes_ship=3, hes_total=3, compare=0.4, views=5, acc=0.6, returns=0.4, mobile=0.55, returning=0.70, prior=2.0),
    "split_payment":   dict(cart=260, hes_ship=6, hes_total=24, compare=1.0, views=7, acc=0.6, returns=1.6, mobile=0.60, returning=0.45, prior=0.6),
    "shipping_hunter": dict(cart=55,  hes_ship=22, hes_total=7, compare=1.0, views=5, acc=0.5, returns=1.2, mobile=0.60, returning=0.40, prior=0.5),
    "price_sensitive": dict(cart=85,  hes_ship=9, hes_total=12, compare=3.2, views=11, acc=0.8, returns=1.4, mobile=0.65, returning=0.35, prior=0.3),
    "bundle_seeker":   dict(cart=95,  hes_ship=6, hes_total=8, compare=1.2, views=8, acc=3.2, returns=1.0, mobile=0.55, returning=0.45, prior=0.7),
    "browser":         dict(cart=70,  hes_ship=4, hes_total=4, compare=0.8, views=3, acc=0.4, returns=0.3, mobile=0.60, returning=0.30, prior=0.1),
}

# Named presets for the "shopper replay" demo, mapped to archetypes.
PERSONAS = {
    "split-payment person": "split_payment",
    "will buy anyway": "will_buy_anyway",
    "free-shipping hunter": "shipping_hunter",
    "price-sensitive student": "price_sensitive",
    "bundle lover": "bundle_seeker",
    "just browsing": "browser",
}


@dataclass
class Population:
    signals: pd.DataFrame          # what the engine may see (store features minus intent_score)
    uci: pd.DataFrame              # the real UCI behaviour row behind each shopper
    archetype: np.ndarray
    p_true: pd.DataFrame           # columns = INCENTIVES, hidden P(buy | incentive)
    pl_true: pd.DataFrame          # columns = INCENTIVES, hidden P(pays with Pay Later | buys, incentive)


def _uci_pools(uci: pd.DataFrame) -> dict[str, np.ndarray]:
    bought = uci.index[uci["Revenue"]].to_numpy()
    no_val = uci.index[(~uci["Revenue"]) & (uci["PageValues"] == 0)].to_numpy()
    engaged = uci.index[(~uci["Revenue"]) & (uci["ProductRelated"] >= 5)].to_numpy()
    return {"bought": bought, "no_val": no_val, "engaged": engaged}


def generate(n: int, uci: pd.DataFrame, seed: int = 0, archetype: str | None = None) -> Population:
    rng = np.random.default_rng(seed)
    names = list(ARCHETYPES)
    shares = np.array([ARCHETYPES[a]["share"] for a in names])
    arch = np.array([archetype] * n) if archetype else rng.choice(names, size=n, p=shares / shares.sum())

    pools = _uci_pools(uci)
    rows = np.empty(n, dtype=int)
    for i, a in enumerate(arch):
        if a == "will_buy_anyway":
            pool = pools["bought"] if rng.random() < 0.7 else pools["engaged"]
        elif a == "browser":
            pool = pools["no_val"]
        else:
            pool = pools["engaged"] if rng.random() < 0.75 else pools["bought"]
        rows[i] = rng.choice(pool)
    uci_rows = uci.loc[rows].reset_index(drop=True)

    S = pd.DataFrame([SIGNALS[a] for a in arch])
    cart = np.round(np.exp(np.log(S["cart"]) + rng.normal(0, 0.45, n)), 2).clip(12, 1400)
    sig = pd.DataFrame({
        "cart_value": cart,
        "n_items": 1 + rng.poisson((cart / 120).clip(0, 3)),
        "time_on_page_s": np.round(rng.gamma(2.0, 8 + S["hes_total"] + S["hes_ship"]), 1),
        "product_views": rng.poisson(S["views"]),
        "cart_returns": rng.poisson(S["returns"]),
        "compare_events": rng.poisson(S["compare"]),
        "hesitation_after_shipping_s": np.round(rng.exponential(S["hes_ship"]), 1),
        "hesitation_after_total_s": np.round(rng.exponential(S["hes_total"]), 1),
        "accessory_views": rng.poisson(S["acc"]),
        "is_mobile": (rng.random(n) < S["mobile"]).astype(int),
        "is_returning": (rng.random(n) < S["returning"]).astype(int),
    })
    sig["prior_orders"] = np.where(sig["is_returning"] == 1, rng.poisson(S["prior"]), 0)

    # Hidden truth with per-shopper heterogeneity.
    p0 = np.array([ARCHETYPES[a]["p0"] for a in arch])
    p0 = np.clip(p0 * np.exp(rng.normal(0, 0.25, n)), 0.005, 0.97)
    p_true = {"none": p0}
    for inc in INCENTIVES[1:]:
        base = np.array([ARCHETYPES[a]["lift"][inc] for a in arch])
        lift = base * np.exp(rng.normal(0, 0.35, n))
        if inc == "paylater":
            # instalments matter more on bigger carts; outside the Pay in 4 range they do nothing
            lift = lift * np.clip(cart / 150, 0.3, 1.4)
            lift = np.where([paylater_eligible(c) for c in cart], lift, 0.0)
        if inc == "free_shipping":
            lift = lift * np.clip(60 / cart, 0.35, 1.5)  # $8.99 matters less on a big cart
        p_true[inc] = np.clip(p0 + lift, 0, 0.99)
    p_true = pd.DataFrame(p_true)[INCENTIVES]

    pl = np.array([ARCHETYPES[a]["pl_use"] for a in arch])
    elig = np.array([paylater_eligible(c) for c in cart])
    pl_true = pd.DataFrame({inc: np.where(elig, pl[:, 1] if inc == "paylater" else pl[:, 0], 0.0) for inc in INCENTIVES})

    return Population(sig, uci_rows, arch, p_true, pl_true)


def randomized_log(pop: Population, seed: int = 1) -> pd.DataFrame:
    """A merchant's exploration log: one uniformly random incentive per shopper, with outcomes.
    This is what the uplift models train on (never on the hidden truth)."""
    rng = np.random.default_rng(seed)
    n = len(pop.signals)
    arm = rng.choice(INCENTIVES, size=n)
    p = pop.p_true.to_numpy()[np.arange(n), [INCENTIVES.index(a) for a in arm]]
    bought = (rng.random(n) < p).astype(int)
    plp = pop.pl_true.to_numpy()[np.arange(n), [INCENTIVES.index(a) for a in arm]]
    used_pl = ((rng.random(n) < plp) & (bought == 1)).astype(int)
    out = pop.signals.copy()
    out["arm"] = arm
    out["bought"] = bought
    out["used_paylater"] = used_pl
    return out
