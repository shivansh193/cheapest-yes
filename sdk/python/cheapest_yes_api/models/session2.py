from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, OptionalNullable, SdkBaseModel


class Session2(SdkBaseModel):
    """session"""

    time_on_page_s: float = 0.0
    """time on the checkout page (s)"""

    product_views: int = 0
    """product pages viewed this session"""

    cart_returns: int = 0
    """times the shopper came back to the cart"""

    compare_events: int = 0
    """price-comparison signals (copied a product name, switched tabs)"""

    hesitation_after_shipping_s: float = 0.0
    """idle time right after the shipping cost was shown (s)"""

    hesitation_after_total_s: float = 0.0
    """idle time right after the order total was shown (s)"""

    accessory_views: int = 0
    """accessory / add-on products viewed"""

    is_mobile: int = 0
    """device class is mobile"""

    is_returning: int = 0
    """returning visitor"""

    prior_orders: int = 0
    """past orders with this merchant (logged-in only)"""

    browse_seconds: OptionalNullable[float] = UNSET
    """seconds spent on product pages (feeds the intent model)"""

    intent_score: OptionalNullable[float] = UNSET
    """optional precomputed purchase-intent score"""


class Session2Dict(TypedDict):
    time_on_page_s: NotRequired[float]
    product_views: NotRequired[int]
    cart_returns: NotRequired[int]
    compare_events: NotRequired[int]
    hesitation_after_shipping_s: NotRequired[float]
    hesitation_after_total_s: NotRequired[float]
    accessory_views: NotRequired[int]
    is_mobile: NotRequired[int]
    is_returning: NotRequired[int]
    prior_orders: NotRequired[int]
    browse_seconds: NotRequired[float | None]
    intent_score: NotRequired[float | None]
