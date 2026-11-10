# Evidence

Every number here was checked against its source on 2026-11-10. Where a source could not be opened directly, that is stated.

## Cart and checkout abandonment

**Baymard Institute, "Cart Abandonment Rate"** — https://baymard.com/lists/cart-abandonment-rate

- Documented average online cart abandonment rate: **70.22%**, the unweighted average of 50 studies published 2006–2025.
- Reasons for abandoning during checkout, excluding shoppers who were "just browsing" (that group was 42% of US online shoppers who abandoned):
  - Extra costs too high (shipping, tax, fees): **40%**
  - Delivery too slow: 20%
  - Didn't trust the site with card details: 19%
  - Site required account creation: 18%
  - Checkout too long or complicated: 17%
  - Couldn't see the total order cost up front: 12%
  - Not enough payment methods: 9%

The page does not state the survey sample size or year next to the list; quote it as "Baymard Institute's checkout-abandonment survey" with the link.

## What PayPal Pay Later costs a merchant (central to the pitch)

**PayPal US merchant fees page** — https://www.paypal.com/us/business/paypal-business-fees (page says "Last Updated: November 4, 2026")

| Transaction type | Rate |
|---|---|
| PayPal Checkout | 3.49% + fixed fee |
| PayPal Pay Later options | **4.99% + fixed fee** |
| Fixed fee (USD) | 0.49 USD |

So in the US, a Pay Later order costs the merchant **1.5 percentage points more** than a standard PayPal Checkout order. The fixed fee is the same.

**PayPal UK merchant fees page** — https://www.paypal.com/uk/business/paypal-business-fees (page says "Last Updated: 1, October 2026")

| Transaction type | Rate |
|---|---|
| Buy Now Pay Later Transactions | **3.9% + fixed fee** |
| All Other Commercial Transactions | 2.9% + fixed fee |

UK: **1.0 percentage point more** than standard.

**Conflicting older claims.** PayPal's Braintree guide (https://developer.paypal.com/braintree/articles/guides/payment-methods/paypal-pay-later-offers) says Pay Later offers are included "at no additional cost to you unless you are in the US". PayPal enterprise marketing pages also say "no extra cost". The current fee schedules above are the binding numbers, so this project uses them.

**Consequence for the product.** Pay Later is not free in the US or UK. It is still usually the cheapest incentive: on a $240 cart the extra fee is about $3.60, against $24 for a 10% discount. And the merchant only pays it on orders the shopper actually funds with Pay Later; showing the message costs nothing. The decision engine models Pay Later cost as `P(shopper picks Pay Later | converts) × 1.5% × order value` (US).

## Regulatory context: why prices never go up

- **FTC surveillance pricing 6(b) study.** Launched July 2024 with orders to eight firms; preliminary research summaries released January 2025: https://www.ftc.gov/system/files/ftc_gov/pdf/p246202_surveillancepricing6bstudy_researchsummaries_redacted.pdf. The FTC said the summaries are initial findings and not an assessment of whether anyone broke the law.
- **New York Algorithmic Pricing Disclosure Act**, N.Y. Gen. Bus. Law § 349-A, in effect since **November 10, 2025**. A business that sets a price with an algorithm using a consumer's personal data must show a clear and conspicuous disclosure that the price was set that way. Summary: https://www.kelleydrye.com/viewpoints/blogs/ad-law-access/new-yorks-algorithmic-pricing-disclosure-law-takes-effect

Cheapest Yes never raises a price above list and never sets a personalised price from personal data. It chooses among merchant-defined incentives using session behaviour only. Whether a personalised *discount* triggers § 349-A disclosure is a legal question for each merchant; the product shows a plain "why you're seeing this offer" note on every incentive anyway.

## Still to verify

- PayPal's own published study numbers on Pay Later conversion / AOV lift (PayPal marketing pages blocked automated reading; to check by hand before quoting in the video).
