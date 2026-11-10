"""Order economics. Pure functions shared by the decision engine, the simulator and the eval,
so the profit the engine optimises is exactly the profit the eval scores."""
from __future__ import annotations

from dataclasses import dataclass

from .config import DEFAULT, DISCOUNT_PCT, MerchantConfig


@dataclass(frozen=True)
class OrderAmounts:
    item_total: float      # merchandise at list price (add-on line is $0)
    shipping: float
    discount: float
    total: float           # what the shopper pays

    def check_ceiling(self, list_item_total: float, cfg: MerchantConfig = DEFAULT) -> None:
        """The one rule: nobody pays more than list. Raises if violated."""
        if self.discount < 0 or self.shipping < 0:
            raise ValueError("negative discount or shipping")
        if self.item_total > round(list_item_total, 2) + 1e-9:
            raise ValueError("item total above list price")
        if self.total > round(list_item_total + cfg.shipping_fee, 2) + 1e-9:
            raise ValueError("order total above list price plus standard shipping")


def amounts(item_total: float, incentive: str, cfg: MerchantConfig = DEFAULT) -> OrderAmounts:
    item_total = round(item_total, 2)
    shipping = 0.0 if incentive == "free_shipping" else cfg.shipping_fee
    pct = min(DISCOUNT_PCT.get(incentive, 0.0), cfg.max_discount_pct)
    discount = round(item_total * pct, 2)
    total = round(item_total + shipping - discount, 2)
    return OrderAmounts(item_total, shipping, discount, total)


def paylater_eligible(total: float, cfg: MerchantConfig = DEFAULT) -> bool:
    return cfg.paylater_min_total <= total <= cfg.paylater_max_total


def incentive_cost(item_total: float, incentive: str, cfg: MerchantConfig = DEFAULT) -> float:
    """Direct cost to the merchant if the order happens (excludes the Pay Later fee, which
    depends on whether the shopper actually pays with Pay Later; see profit_if_buy)."""
    if incentive == "free_shipping":
        return cfg.shipping_fee
    if incentive == "addon":
        return cfg.addon_cogs
    if incentive in DISCOUNT_PCT:
        return round(item_total * min(DISCOUNT_PCT[incentive], cfg.max_discount_pct), 2)
    return 0.0


def profit_if_buy(item_total: float, incentive: str, p_paylater: float, cfg: MerchantConfig = DEFAULT) -> float:
    """Merchant profit on a completed order, in expectation over the payment method.

    margin on merchandise - incentive cost - PayPal fee - P(paid with Pay Later) x Pay Later surcharge.
    Shipping is charged at cost, so it nets to zero unless it's waived (then it's the incentive cost).
    """
    a = amounts(item_total, incentive, cfg)
    margin = cfg.gross_margin_rate * item_total
    fee = cfg.paypal_pct * a.total + cfg.paypal_fixed
    pl_extra = p_paylater * cfg.paylater_extra_pct * a.total
    return margin - incentive_cost(item_total, incentive, cfg) - fee - pl_extra
