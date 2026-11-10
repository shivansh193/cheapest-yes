"""Merchant economics and guardrail settings. One place, so judges can audit every number.

Fees are PayPal's published US rates (https://www.paypal.com/us/business/paypal-business-fees,
page last updated 2026-11-04): PayPal Checkout 3.49% + $0.49; Pay Later 4.99% + $0.49.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Incentive ladder, cheapest-for-the-merchant first. Ties in expected profit go to the earlier one.
INCENTIVES = ["none", "paylater", "free_shipping", "addon", "discount_5", "discount_10"]

LABELS = {
    "none": "No incentive",
    "paylater": "PayPal Pay Later",
    "free_shipping": "Free shipping",
    "addon": "Free add-on",
    "discount_5": "5% off",
    "discount_10": "10% off",
}

DISCOUNT_PCT = {"discount_5": 0.05, "discount_10": 0.10}


@dataclass(frozen=True)
class MerchantConfig:
    gross_margin_rate: float = 0.40          # margin on merchandise before payment fees
    shipping_fee: float = 8.99               # what the shopper is charged; equals the merchant's cost
    paypal_pct: float = 0.0349               # PayPal Checkout
    paypal_fixed: float = 0.49
    paylater_extra_pct: float = 0.0150       # Pay Later 4.99% minus Checkout 3.49%
    paylater_min_total: float = 30.0         # Pay in 4 range is $30-$1,500
    paylater_max_total: float = 1500.0
    addon_name: str = "Travel case (free gift)"
    addon_cogs: float = 4.00                 # merchant's cost of the add-on
    addon_list_price: float = 19.00          # shown value; charged at $0
    max_discount_pct: float = 0.10           # merchant cap; the engine never exceeds it
    daily_incentive_budget: float = 500.0    # expected incentive spend allowed per day
    max_incentives_per_shopper_7d: int = 2   # anti-gaming: repeat abandoners stop getting offers
    min_gain: float = 0.50                   # an incentive must beat "none" by at least this ($, expected)
    allowed: tuple[str, ...] = field(default_factory=lambda: tuple(INCENTIVES))


DEFAULT = MerchantConfig()
