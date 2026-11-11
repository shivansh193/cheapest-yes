# Cheapest Yes

**For every hesitant shopper, find the cheapest thing that turns "maybe" into "yes".** Usually that's PayPal Pay Later: it costs the merchant a fraction of a discount, and only when the shopper actually uses it. Only when that won't work does Cheapest Yes offer free shipping, then a free add-on, and a small discount as a last resort. It maximises the merchant's expected profit after incentive cost, not conversion.

**The one rule: list price is the ceiling.** Incentives only add value or lower the price. Nobody ever pays more than list, and that's enforced in code and covered by tests.

Built for the PayPal AI Hackathon 2026, with **PayPal** (Orders v2, JS SDK, Pay Later messaging, signature-verified webhooks) and **AI** (calibrated purchase-intent and uplift models, SHAP explanations, Gemini-written summaries and a merchant copilot).

| | |
|---|---|
| Video (2:52) | **https://youtu.be/_RMi_d4PXs0** |
| Live demo | **https://cheapest-yes.onrender.com** (store), [/replay](https://cheapest-yes.onrender.com/replay), [/dashboard](https://cheapest-yes.onrender.com/dashboard), [/docs](https://cheapest-yes.onrender.com/docs) |
| Payments | PayPal **sandbox** only. Log in at checkout with any PayPal sandbox *personal* account. |
| Eval | [docs/EVAL.md](docs/EVAL.md) (regenerate with `make eval`) |
| Evidence | [docs/EVIDENCE.md](docs/EVIDENCE.md) · integration spikes: [docs/SPIKES.md](docs/SPIKES.md) |

> The hosted demo runs on Render's free plan. The first request after it has been idle can take about a minute while it wakes up.

## The problem

- About **70%** of online carts are abandoned (Baymard Institute, average of 50 studies, [source](https://baymard.com/lists/cart-abandonment-rate)).
- The top reason shoppers give for abandoning checkout is **extra costs too high** (shipping, tax, fees), at **40%** of those not "just browsing" (same source).
- Merchants usually answer with blanket discounts. That gives margin away to people who would have bought anyway, teaches shoppers to wait for coupons, and treats price as the only lever.
- Personalised *surcharges* are under regulatory scrutiny: the FTC's surveillance-pricing study ([2025 summaries](https://ftc.gov/system/files/ftc_gov/pdf/p246202_surveillancepricing6bstudy_researchsummaries_redacted.pdf)) and New York's Algorithmic Pricing Disclosure Act (GBL § 349-A, in force since Nov 10, 2025). Cheapest Yes never raises a price and never sets a price from personal data.

### What Pay Later actually costs a merchant

PayPal's own US fee page (updated Nov 4, 2026) lists **PayPal Checkout at 3.49% + $0.49** and **Pay Later at 4.99% + $0.49**: **1.5 points more**, not free. The UK is +1.0 point. On a $240 cart that's about **$3.60**, against **$24** for a 10% discount. And the merchant only pays it on orders the shopper actually pays with Pay Later. So the engine prices Pay Later as:

`expected Pay Later cost = P(pays with Pay Later | buys) × 1.5% × order total`

Details and sources: [docs/EVIDENCE.md](docs/EVIDENCE.md).

## How it decides

For each allowed incentive *o* in the ladder `none → Pay Later → free shipping → free add-on → 5% off → 10% off`:

```
profit_if_buy(o) = 40% margin on items − incentive cost(o) − PayPal fee − P(Pay Later | buy, o) × 1.5% × total
EP(o)            = P(buy | o) × profit_if_buy(o)
gain(o)          = EP(o) − EP(none)
                 = P(buy|o) × (margin − cost(o)) − P(buy|none) × margin
```

It picks the incentive with the largest gain, and **no incentive unless the best one beats doing nothing by at least $0.50**. Ties go to the cheaper rung. Giving an incentive to someone who'd have bought anyway is counted as a cost. The engine is deterministic given the model outputs ([cy/engine.py](cy/engine.py)); the LLM never decides anything.

The ladder isn't a fixed order. On a $56 cart, 10% off ($5.60) is cheaper than free shipping ($8.99), and the engine knows that.

## Signals

Session behaviour only. **Never used:** demographics, location or location-based income proxies, IP enrichment, or protected attributes. (The author's earlier pricing project used pincode income and IP signals; none of that code came across.)

| Feature | What it is |
|---|---|
| `cart_value`, `n_items` | cart value and size |
| `time_on_page_s` | time on the checkout page |
| `product_views`, `browse_seconds` | product pages viewed and time spent on them |
| `cart_returns` | times the shopper came back to the cart |
| `compare_events` | price-comparison signals: copied a product name, switched tabs |
| `hesitation_after_shipping_s` | idle time right after the shipping cost was shown |
| `hesitation_after_total_s` | idle time right after the order total was shown |
| `accessory_views` | accessory / add-on products viewed |
| `is_mobile` | device class |
| `is_returning`, `prior_orders` | returning visitor; past orders with this merchant |
| `intent_score` | purchase-intent score from the public-data model |
| `shipping_share` | derived: shipping fee ÷ cart value |

The dashboard's **fairness panel** reports offer and discount rates by device class and by new versus returning visitor, from the live log and from the simulator.

## AI components

1. **Purchase-intent model.** LightGBM with isotonic calibration, trained on the public UCI Online Shoppers Purchasing Intention dataset. Test AUC **0.910**, Brier 0.075 ([calibration plot](reports/intent_calibration.png)).
2. **Uplift / response models.** One calibrated classifier per incentive (a T-learner), giving P(buy | incentive, session). There's also a model for P(pays with Pay Later | buys), which sets Pay Later's real cost. They are trained on a merchant's *randomized exploration log* of observed outcomes, never on hidden truth. The same recipe was validated on real randomized data, the Criteo uplift dataset: **AUUC 1.73× random targeting**, and 4.6% uplift in the top 20% the model picks against 1.2% on average ([Qini curve](reports/criteo_qini.png)).
3. **SHAP explanations.** TreeSHAP via LightGBM's `pred_contrib`, on the *uplift* (logit P(buy|o) − logit P(buy|none)), turned into reasons like "they paused 38s after seeing the total".
4. **Gemini.** It writes one plain sentence per decision for the merchant from those reasons. It also powers a **merchant copilot** that answers questions ("which incentive made the most profit?") from SQL aggregates of the decision log only. It falls back across lighter Gemini models when the free tier is busy, and the deterministic sentence is always shown.

## Results (simulator A/B, 20,000 fresh shoppers, 95% bootstrap CIs)

| Policy | Profit per 1,000 shoppers | vs blanket 10% off | Conversion | Incentive spend / 1k | Spend wasted on would-buy-anyway / 1k |
|---|---|---|---|---|---|
| No incentive | $15,291 | −$187 | 34.0% | $0 | $0 |
| Blanket 10% off | $15,479 | — | 47.8% | $5,929 | $4,276 |
| Always show Pay Later | $22,936 | +$7,457 | 42.3% | $416 | $166 |
| **Cheapest Yes** | **$23,769** | **+$8,290 (+7,924 to +8,656)** | 49.8% | $1,681 | $798 |
| Cheapest Yes without Pay Later | $17,182 | +$1,704 | 45.1% | $2,347 | $1,413 |
| Oracle (sees hidden truth) | $24,994 | +$9,516 | 54.4% | $2,005 | $802 |

- **Ablation:** taking Pay Later out of the ladder costs **$6,587 per 1,000 shoppers**. The cheap nudge is most of the value.
- **Honest comparison:** simply always showing Pay Later gets most of the way there. Cheapest Yes adds **+$833 per 1k shoppers (95% CI +720 to +955)** on top, by using paid incentives only where they pay off.
- It picks the same incentive as the oracle for 47% of shoppers and reaches 95% of the oracle's profit.

**These are simulator results, not field results.** The simulator's archetypes and effect sizes are assumptions; see [Limitations](#limitations). Full tables, mix by hidden archetype and fairness: [docs/EVAL.md](docs/EVAL.md).

## Guardrails

All are enforced in [cy/engine.py](cy/engine.py) and [cy/economics.py](cy/economics.py) and tested in [tests/test_guardrails.py](tests/test_guardrails.py) (55 tests):

- **List-price ceiling:** every decision runs `check_ceiling()`. Line prices are never above list, the total is never above list plus standard shipping, and discounts and shipping are never negative.
- **Max discount:** set by the merchant (default 10%).
- **Daily incentive budget:** expected incentive spend from live checkouts is tracked. Once the budget is used up, only no-cost options remain.
- **Per-shopper cap:** a shopper gets at most 2 paid offers per 7 days (shopper id stored only as a hash), so abandoning repeatedly doesn't farm discounts. Pay Later messaging changes no price, so it stays available.
- **Server-side amounts:** the browser only sends a decision id. Order amounts are rebuilt on the server from the stored decision and catalog prices.

## PayPal integration

- **Orders v2:** `POST /v2/checkout/orders` with `amount.breakdown` (`item_total`, `shipping`, `discount`). Free shipping sets `shipping` to 0, discounts go in `discount`, and the free add-on is a $0 line item. Every order carries `custom_id = cheapest-yes:<decision id>`.
- **JS SDK:** PayPal buttons with `enable-funding=paylater`; `onApprove` captures on the server.
- **Pay Later messaging:** `paypal.Messages` with the exact cart amount when Pay Later is the chosen incentive. In the sandbox (US buyer) it renders "Pay in 4" for smaller carts and Pay Monthly for larger ones.
- **Capture:** `POST /v2/checkout/orders/{id}/capture`. The decision log stores the capture id, the actual PayPal fee from `seller_receivable_breakdown`, and the funding source.
- **Webhooks:** `CHECKOUT.ORDER.APPROVED` and `PAYMENT.CAPTURE.COMPLETED/DENIED/REFUNDED`. Each is verified with `POST /v1/notifications/verify-webhook-signature` before it's recorded; events from other apps are dropped.

## Sponsor tools

- **Channel3:** a real product catalog with prices and images for the demo store ([app/catalog.py](app/catalog.py), snapshot in `artifacts/catalog.json`).
- **AG Grid:** the merchant decision log (sorting, filtering, quick search, pagination, PayPal ids per row).
- **Render:** hosts the app and API.
- **APIMatic:** the public `/decide` API is exported as OpenAPI ([openapi/cheapest-yes.json](openapi/cheapest-yes.json)), validated with the APIMatic CLI, and turned into **Python and TypeScript SDKs** ([sdk/](sdk/)). See [examples/sdk_decide.py](examples/sdk_decide.py), which calls the hosted API through the generated Python SDK.

## Use the API

```bash
curl -s https://cheapest-yes.onrender.com/decide -H 'Content-Type: application/json' -d '{
  "cart": [{"id": "sku-123", "title": "Wireless headphones", "price": 240}],
  "session": {"hesitation_after_total_s": 38, "cart_returns": 2, "product_views": 6}
}'
```

```python
from cheapest_yes_api import CheapestYesApiClient   # pip install ./sdk/python
with CheapestYesApiClient() as client:
    d = client.decisions.decide({"cart": [{"id": "sku-123", "title": "Headphones", "price": 240.0}],
                                 "session": {"hesitation_after_total_s": 38}})
    print(d.incentive, d.amounts.total, d.explanation)
```

## Run it locally

```bash
python -m venv .venv && .venv/Scripts/activate      # or source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                                  # fill in sandbox values
make test
make run                                              # http://127.0.0.1:8017
```

| Variable | What |
|---|---|
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | a PayPal **sandbox** REST app (developer.paypal.com → Apps & Credentials). The code refuses non-sandbox URLs. |
| `PAYPAL_API_BASE` | `https://api-m.sandbox.paypal.com` |
| `PAYPAL_WEBHOOK_ID` | id of a sandbox webhook pointing at `<your url>/webhooks/paypal` |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Google AI Studio key (optional; template explanations work without it) |
| `CHANNEL3_API_KEY` | only needed to refresh the catalog (`make catalog`); the snapshot ships in the repo |

To check out you need a PayPal sandbox **personal** account (developer.paypal.com → Sandbox → Accounts). Models are pre-trained in `artifacts/`; `make train` and `make eval` rebuild them. The UCI data downloads automatically, and Criteo (~311 MB) downloads on first `make eval`.

## Data sources and licences

| Data | Use | Licence |
|---|---|---|
| [UCI Online Shoppers Purchasing Intention](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset) (Sakar & Kastro, 2018, doi:10.24432/C5F88Q) | intent model; real browsing sessions behind each simulated shopper | CC BY 4.0, redistributed in `artifacts/uci_sessions.parquet` with attribution |
| [Criteo Uplift v2.1](https://ailab.criteo.com/criteo-uplift-prediction-dataset/) (Diemert et al., AdKDD 2018), via Criteo's [Hugging Face mirror](https://huggingface.co/datasets/criteo/criteo-uplift) | validating the uplift method (Qini) | CC BY-NC-SA 4.0. Not redistributed; no model trained on it ships in the app |
| Channel3 product API | demo catalog | Channel3 terms; images served from Channel3's CDN |
| Simulator ([cy/sim.py](cy/sim.py)) | incentive responses with hidden truth | this repo (MIT) |

## Limitations

- The incentive responses come from a **simulator**. Its six archetypes and effect sizes (for example, how much Pay Later helps a split-payment shopper) are assumptions. The eval shows the engine can recover those effects from a randomized log and turn them into profit; it doesn't show what real shoppers do. A real deployment would start with a randomized exploration period.
- Browsing behaviour is real (UCI sessions), but cart, hesitation and comparison signals are simulated. In the live store, the intent model sees only the fields we can observe and dataset medians for the rest.
- The Criteo check is real randomized data, but in advertising, not checkout incentives.
- The simulator A/B doesn't apply the daily budget or per-shopper cap; the live engine does.
- On Render's free plan, the SQLite decision log resets when the instance restarts. The seeded simulated history is rebuilt automatically, but sandbox orders from before a restart are lost.
- Pay Later fees are the US rates. Messaging and eligibility were verified for a US buyer in the sandbox.
- The free Gemini tier has small daily quotas, so LLM summaries can be missing at busy times. The deterministic explanation is always there.

## What's new in this repo

Everything here was written during the hackathon. From the author's earlier `wtp-dynamic-pricing-engine` repo, only two patterns were adapted:
- a warm model singleton whose SHAP explanations never crash ([cy/models.py](cy/models.py));
- the matplotlib plot style.

That project set personalised prices, including markups; this one forbids markups, uses no location or income signals, and optimises incentive choice rather than price.

## Licence

MIT. See [LICENSE](LICENSE).
