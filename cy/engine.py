"""Decision engine. Deterministic given model outputs: same inputs, same decision.

For each allowed incentive o:
    EP(o)   = P(buy | o) x profit_if_buy(o)
    gain(o) = EP(o) - EP(none)
            = P(buy|o) x (margin - cost(o)) - P(buy|none) x margin      (the PRD formula,
              with payment fees and Pay Later's expected surcharge folded into margin/cost)
Pick the incentive with the largest gain; pick "none" unless the best gain beats min_gain.
Ties go to the cheaper rung of the ladder: Pay Later -> free shipping -> add-on -> discount.

Guardrails (all enforced here, all covered by tests):
  - list price is the ceiling: OrderAmounts.check_ceiling() runs on every decision
  - discounts never exceed the merchant's max_discount_pct
  - expected incentive spend must fit in today's remaining budget
  - a shopper who already got max_incentives_per_shopper_7d offers gets no further paid incentive
    (Pay Later messaging changes no price, so it stays available)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd

from .config import DEFAULT, DISCOUNT_PCT, INCENTIVES, LABELS, MerchantConfig
from .economics import amounts, incentive_cost, paylater_eligible, profit_if_buy
from .features import FEATURE_ORDER, derive
from .models import ResponseModel


@dataclass
class Option:
    incentive: str
    allowed: bool
    blocked_by: str | None
    p_buy: float
    p_paylater: float
    profit_if_buy: float
    expected_profit: float
    gain_vs_none: float
    expected_spend: float


@dataclass
class Decision:
    incentive: str
    label: str
    options: list[Option]
    amounts: dict
    expected_gain: float
    reasons: list[dict]
    explanation: str
    guardrails: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _expected_spend(item_total: float, inc: str, p: float, p_pl: float, p_pl_none: float, cfg: MerchantConfig) -> float:
    """Expected incentive cost charged against the daily budget."""
    a = amounts(item_total, inc, cfg)
    pl_extra = max(p_pl - p_pl_none, 0) * cfg.paylater_extra_pct * a.total
    return p * (incentive_cost(item_total, inc, cfg) + pl_extra)


def choose_batch(X: pd.DataFrame, model: ResponseModel, cfg: MerchantConfig = DEFAULT,
                 exclude: frozenset[str] = frozenset()) -> pd.Series:
    """Vectorised version of decide() for the eval: same scoring, no per-row guardrail state
    (daily budget and per-shopper caps are not applied in the simulator A/B)."""
    import numpy as np

    p = model.p_buy(X)
    pl = model.p_paylater(X)
    item = X["cart_value"].to_numpy(dtype=float)
    gains = {}
    ep_none = None
    for inc in INCENTIVES:
        totals = np.array([amounts(v, inc, cfg).total for v in item])
        elig = np.array([paylater_eligible(t, cfg) for t in totals])
        p_pl = np.where(elig, pl[inc].to_numpy(), 0.0)
        pib = np.array([profit_if_buy(v, inc, q, cfg) for v, q in zip(item, p_pl)])
        ep = p[inc].to_numpy() * pib
        if inc == "none":
            ep_none = ep
        ok = inc in cfg.allowed and inc not in exclude
        if inc == "paylater":
            ok_vec = elig & ok
        elif inc in DISCOUNT_PCT:
            ok_vec = np.full(len(X), ok and DISCOUNT_PCT[inc] <= cfg.max_discount_pct + 1e-9)
        else:
            ok_vec = np.full(len(X), ok)
        gains[inc] = np.where(ok_vec, np.round(ep - ep_none, 2), -np.inf)
    G = pd.DataFrame(gains, index=X.index)[INCENTIVES]
    # ties -> earlier (cheaper) rung: idxmax returns the first max in column order
    choice = G.idxmax(axis=1)
    best_gain = G.max(axis=1)
    choice[(choice != "none") & (best_gain < cfg.min_gain)] = "none"
    return choice


def decide(
    session: dict,
    model: ResponseModel,
    cfg: MerchantConfig = DEFAULT,
    budget_spent_today: float = 0.0,
    shopper_incentives_7d: int = 0,
) -> Decision:
    item_total = float(session["cart_value"])
    X = derive(pd.DataFrame([{f: float(session.get(f, 0) or 0) for f in FEATURE_ORDER}]))
    p = model.p_buy(X).iloc[0]
    pl = model.p_paylater(X).iloc[0]
    budget_left = max(cfg.daily_incentive_budget - budget_spent_today, 0.0)

    opts: list[Option] = []
    guard_notes: list[str] = []
    ep_none = float(p["none"]) * profit_if_buy(item_total, "none", float(pl["none"]), cfg)
    for inc in INCENTIVES:
        blocked = None
        total = amounts(item_total, inc, cfg).total
        if inc not in cfg.allowed:
            blocked = "disabled by merchant"
        elif inc == "paylater" and not paylater_eligible(total, cfg):
            blocked = f"order total outside Pay Later range (${cfg.paylater_min_total:.0f}-${cfg.paylater_max_total:,.0f})"
        elif inc in DISCOUNT_PCT and DISCOUNT_PCT[inc] > cfg.max_discount_pct + 1e-9:
            blocked = "above merchant's max discount"
        p_pl = float(pl[inc]) if paylater_eligible(total, cfg) else 0.0
        pib = profit_if_buy(item_total, inc, p_pl, cfg)
        ep = float(p[inc]) * pib
        spend = _expected_spend(item_total, inc, float(p[inc]), p_pl, float(pl["none"]), cfg) if inc != "none" else 0.0
        if blocked is None and inc not in ("none", "paylater"):
            if shopper_incentives_7d >= cfg.max_incentives_per_shopper_7d:
                blocked = "shopper already received the maximum offers this week"
            elif spend > budget_left:
                blocked = "daily incentive budget used up"
        if blocked and inc != "none":
            guard_notes.append(f"{LABELS[inc]}: {blocked}")
        opts.append(Option(inc, blocked is None, blocked, round(float(p[inc]), 4), round(p_pl, 4),
                           round(pib, 2), round(ep, 2), round(ep - ep_none, 2), round(spend, 2)))

    allowed = [o for o in opts if o.allowed]
    best = max(allowed, key=lambda o: (round(o.gain_vs_none, 2), -INCENTIVES.index(o.incentive)))
    if best.incentive != "none" and best.gain_vs_none < cfg.min_gain:
        best = next(o for o in opts if o.incentive == "none")

    a = amounts(item_total, best.incentive, cfg)
    a.check_ceiling(item_total, cfg)

    from .explain import reasons_for, template_sentence  # local import keeps engine importable alone

    reasons = reasons_for(X, best.incentive, model, session)
    sentence = template_sentence(best.incentive, reasons, best, opts, session)
    return Decision(
        incentive=best.incentive,
        label=LABELS[best.incentive],
        options=opts,
        amounts=asdict(a),
        expected_gain=best.gain_vs_none,
        reasons=reasons,
        explanation=sentence,
        guardrails=guard_notes,
    )
