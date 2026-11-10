"""Call the hosted Cheapest Yes API with the APIMatic-generated Python SDK.

    pip install ./sdk/python
    python examples/sdk_decide.py
"""
from cheapest_yes_api import CheapestYesApiClient

with CheapestYesApiClient() as client:  # default server: https://cheapest-yes.onrender.com
    d = client.decisions.decide({
        "cart": [{"id": "sku-123", "title": "Wireless headphones", "price": 240.0, "qty": 1}],
        "session": {"hesitation_after_total_s": 38, "cart_returns": 2, "time_on_page_s": 75, "product_views": 6},
        "shopper_id": "sdk-example",
    })
    print(d.incentive, d.amounts.total)
    print(d.explanation)
