"""Session features. Behaviour only.

Never used: demographics, location or location-based income proxies, IP enrichment,
or any protected attribute. Device class and new/returning are used, and the dashboard's
fairness panel reports incentive rates across exactly those groups.
"""
from __future__ import annotations

# name -> plain-English description (also rendered in the README and used in explanations)
STORE_FEATURES: dict[str, str] = {
    "cart_value": "cart value ($)",
    "n_items": "items in cart",
    "time_on_page_s": "time on the checkout page (s)",
    "product_views": "product pages viewed this session",
    "cart_returns": "times the shopper came back to the cart",
    "compare_events": "price-comparison signals (copied a product name, switched tabs)",
    "hesitation_after_shipping_s": "idle time right after the shipping cost was shown (s)",
    "hesitation_after_total_s": "idle time right after the order total was shown (s)",
    "accessory_views": "accessory / add-on products viewed",
    "is_mobile": "device class is mobile",
    "is_returning": "returning visitor",
    "prior_orders": "past orders with this merchant (logged-in only)",
    "intent_score": "purchase-intent score from the public-data model",
}

FEATURE_ORDER = list(STORE_FEATURES)

# Columns from the UCI Online Shoppers Purchasing Intention dataset used by the intent model.
# Region, OperatingSystems, Browser and TrafficType are deliberately dropped: they are coarse
# location / platform proxies and not needed.
UCI_NUMERIC = [
    "Administrative", "Administrative_Duration", "Informational", "Informational_Duration",
    "ProductRelated", "ProductRelated_Duration", "BounceRates", "ExitRates", "PageValues", "SpecialDay",
]
UCI_EXTRA = ["is_returning", "is_weekend"]
UCI_FEATURES = UCI_NUMERIC + UCI_EXTRA
