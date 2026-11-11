# Devpost submission draft

**Name:** Cheapest Yes

**Tagline:** For every hesitant shopper, the cheapest thing that turns "maybe" into "yes". Usually it's PayPal Pay Later. List price is the ceiling.

**Links**
- Try it: https://cheapest-yes.onrender.com (store) · /replay · /dashboard · /docs
- Code: https://github.com/shivansh193/cheapest-yes (MIT)
- Video: https://youtu.be/_RMi_d4PXs0

**Built with:** paypal, paypal-orders-v2, paypal-js-sdk, pay-later, paypal-webhooks, gemini, lightgbm, scikit-learn, shap, python, fastapi, sqlite, javascript, chart.js, ag-grid, channel3, render, apimatic

**Sponsor tools to tick:** AG Grid, APIMatic, Channel3, Render

---

## Inspiration

About 70% of online carts are abandoned, and the top reason shoppers give is extra costs (Baymard). Most merchants respond with a blanket discount. That gives margin away to people who would have paid full price, and it treats price as the only lever. Often a hesitant shopper needs something much cheaper for the merchant: seeing they can split the payment, free shipping, or a small add-on.

## What it does

At checkout, Cheapest Yes looks at session behaviour only: cart size, time on page, returns to the cart, price-comparison signals, and pauses after the shipping cost and total appear. It then picks one incentive, or none, to maximise the merchant's **expected profit after incentive cost**:

- **PayPal Pay Later messaging** with the exact instalment amounts for this cart
- **free shipping**
- **a free add-on**
- **5% or 10% off**, as a last resort

Nobody ever pays more than list price. It's enforced in code and covered by tests.

Three ways to try it:
- **Demo store:** real products from Channel3; check out with PayPal in the sandbox.
- **Shopper replay:** pick a simulated shopper ("split-payment person", "will buy anyway", "price-sensitive student"…), watch their session, see the decision with its reasons, and pay with PayPal.
- **Merchant dashboard:**
  - an AG Grid log of every decision with its PayPal order and capture IDs
  - profit lift against a blanket discount
  - the incentive mix, a fairness panel and the daily budget
  - a Gemini copilot that answers questions from the decision log

## How we built it

**PayPal**
- **Orders v2** with `amount.breakdown`: the discount in `discount`, free shipping as `shipping: 0`, the free add-on as a $0 line item, and a `custom_id` tying each order to its decision.
- **JS SDK buttons** with Pay Later enabled; **Pay Later messaging** with the cart amount.
- **Server-side capture**, recording the real PayPal fee from `seller_receivable_breakdown`.
- **Webhooks** (`PAYMENT.CAPTURE.COMPLETED` and others), each checked with `verify-webhook-signature` before it's recorded.

**AI**
- A calibrated LightGBM **purchase-intent model** trained on the public UCI Online Shoppers dataset (AUC 0.910).
- One calibrated **response model per incentive** (a T-learner) for P(buy | incentive). We validated the same recipe on Criteo's real randomized uplift data: AUUC 1.73× random targeting.
- A model for how likely a shopper is to actually pay with Pay Later. That sets Pay Later's real cost.
- **TreeSHAP** reasons on the uplift: "they paused 38s after seeing the total".
- **Gemini** turns those reasons into one plain sentence and powers the merchant copilot. The LLM never makes the decision; the engine is deterministic given the model outputs.

**The decision**
- `gain(o) = P(buy|o) × (margin − cost(o)) − P(buy|none) × margin`, with PayPal fees folded in.
- Pick the largest gain, and nothing unless it beats doing nothing by at least $0.50.
- Guardrails:
  - the list-price ceiling
  - the merchant's maximum discount
  - a daily incentive budget
  - at most 2 paid offers per shopper per week, so repeat abandoning doesn't farm discounts

**Sponsor tools**
- **Channel3** supplies the real catalog.
- **AG Grid** runs the decision log.
- **Render** hosts the app.
- **APIMatic** validated our OpenAPI spec and generated the Python and TypeScript SDKs for `POST /decide`, which is how another merchant would plug it in.

## Challenges

- **Pay Later isn't free.** We started from the claim that Pay Later costs merchants nothing extra. PayPal's current US fee page says otherwise: 4.99% + $0.49 against 3.49% + $0.49 for standard checkout. So the engine prices it honestly, at 1.5% of the order times the chance the shopper actually uses it. It's still about a seventh of what a 10% discount costs.
- **Evaluating without real experiments.** You can't measure true profit lift from a live store in a weekend. We built a simulator whose shoppers have hidden true responses, grounded each one in a real UCI browsing session, trained only on a randomized exploration log, and scored every policy on fresh shoppers with confidence intervals.

## Accomplishments

Simulator A/B on 20,000 fresh shoppers, profit per 1,000 shoppers:

| Policy | Profit |
|---|---|
| No incentive | $15.3k |
| Blanket 10% off | $15.5k |
| Always show Pay Later | $22.9k |
| **Cheapest Yes** | **$23.8k** (+$8.3k vs blanket 10% off, 95% CI +$7.9k to +$8.7k) |

- Taking Pay Later out of the ladder costs $6.6k per 1,000 shoppers. Most of the value is the cheap nudge.
- Incentive spend wasted on would-buy-anyway shoppers is $0.8k per 1,000 shoppers, against $4.3k for a blanket discount.

These are simulator results, not field results, and the README says exactly which numbers come from public data and which from the simulator.

## What we learned

- The cheapest incentive depends on the cart. On a $56 cart, 10% off is cheaper than $8.99 free shipping.
- "Always show Pay Later" is a strong baseline on its own. The engine's extra value (+$833 per 1,000 shoppers, 95% CI +720 to +955) comes from spending on paid incentives only where they pay off.

## What's next

- A randomized exploration mode for real stores, so the response models learn from live data.
- Per-merchant settings for margin and the incentive ladder.
- Pay Later economics for more markets (the UK rate is +1.0 point).
