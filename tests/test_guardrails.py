"""The one rule and the guardrails, tested."""
import math

import pytest

from cy import sim
from cy.config import DEFAULT, INCENTIVES, MerchantConfig
from cy.data import load_uci
from cy.economics import OrderAmounts, amounts
from cy.engine import choose_batch, decide
from cy.models import get_bundle
from cy.train import with_intent


@pytest.fixture(scope="module")
def shoppers():
    b = get_bundle()
    pop = sim.generate(400, load_uci(), seed=99)
    return b, with_intent(pop, b.intent)


@pytest.mark.parametrize("inc", INCENTIVES)
@pytest.mark.parametrize("cart", [0.01, 12.5, 29.99, 30.0, 99.99, 240.0, 1499.99, 5000.0])
def test_no_incentive_ever_raises_price(inc, cart):
    a = amounts(cart, inc)
    list_total = round(cart + DEFAULT.shipping_fee, 2)
    assert a.item_total == round(cart, 2)
    assert a.total <= list_total
    assert a.discount >= 0 and a.shipping >= 0
    assert math.isclose(a.total, a.item_total + a.shipping - a.discount, abs_tol=0.005)
    a.check_ceiling(cart)


def test_ceiling_check_rejects_markup():
    with pytest.raises(ValueError):
        OrderAmounts(item_total=110, shipping=8.99, discount=0, total=118.99).check_ceiling(100)
    with pytest.raises(ValueError):
        OrderAmounts(item_total=100, shipping=8.99, discount=-5, total=113.99).check_ceiling(100)


def test_engine_decisions_never_exceed_list(shoppers):
    b, X = shoppers
    for i in range(0, len(X), 7):
        s = X.iloc[i].to_dict()
        d = decide(s, b.response)
        assert d.amounts["total"] <= round(s["cart_value"] + DEFAULT.shipping_fee, 2) + 1e-9
        assert d.incentive in INCENTIVES


def test_max_discount_respected(shoppers):
    b, X = shoppers
    cfg = MerchantConfig(max_discount_pct=0.05)
    choices = choose_batch(X, b.response, cfg)
    assert "discount_10" not in set(choices)
    for i in range(0, len(X), 11):
        assert decide(X.iloc[i].to_dict(), b.response, cfg).incentive != "discount_10"
    assert amounts(200, "discount_10", cfg).discount == 10.0  # capped at 5%


def test_budget_exhausted_blocks_paid_incentives(shoppers):
    b, X = shoppers
    for i in range(0, len(X), 9):
        d = decide(X.iloc[i].to_dict(), b.response, budget_spent_today=DEFAULT.daily_incentive_budget)
        assert d.incentive in ("none", "paylater")


def test_per_shopper_cap(shoppers):
    b, X = shoppers
    for i in range(0, len(X), 9):
        d = decide(X.iloc[i].to_dict(), b.response, shopper_incentives_7d=DEFAULT.max_incentives_per_shopper_7d)
        assert d.incentive in ("none", "paylater")


def test_paylater_only_in_range(shoppers):
    b, X = shoppers
    s = X.iloc[0].to_dict()
    s["cart_value"] = 15.0
    d = decide(s, b.response)
    assert d.incentive != "paylater"
    assert any(o.incentive == "paylater" and not o.allowed for o in d.options)


def test_decide_is_deterministic_and_matches_batch(shoppers):
    b, X = shoppers
    batch = choose_batch(X, b.response)
    for i in range(0, len(X), 13):
        s = X.iloc[i].to_dict()
        d1, d2 = decide(s, b.response), decide(s, b.response)
        assert d1.incentive == d2.incentive == batch.iloc[i]
