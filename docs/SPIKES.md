# Spikes

Verify each integration before building UI. Status as of 2026-11-10.

| # | Spike | Status | Result |
|---|---|---|---|
| 1 | Orders v2 sandbox order with `discount` and `shipping: 0` in `amount.breakdown`: create, approve, capture | **Create: pass.** Approve/capture pending | `spikes/spike_orders.py`. Order with item_total 200.00, a $0 add-on line, shipping 0.00, discount 10.00, total 190.00 accepted (HTTP 200, `PAYER_ACTION_REQUIRED`). Awaiting buyer approval in sandbox, then capture |
| 2 | Pay Later messaging + Pay Later funding source in sandbox | **Pass (US buyer)** | `spikes/paylater.html`, JS SDK with `components=buttons,messages,funding-eligibility`, `enable-funding=paylater`, `buyer-country=US`. `isFundingEligible(PAYLATER)` true; Pay Later button renders in the stack and standalone. Messaging is offer-aware: $120 cart → "Pay in 4 interest-free payments of $30.00"; $240 cart → "Starting at $22.93/mo or as low as 0% APR" (Pay Monthly). Demo targets US buyers only; the merchant app is US |
| 3 | Webhook (`CHECKOUT.ORDER.APPROVED`, `PAYMENT.CAPTURE.COMPLETED`) arrives and passes `verify-webhook-signature` | Blocked | Needs a public URL (Render) and a webhook registered on the PayPal app |
| 4 | Channel3 returns real products and images | **Pass** | `spikes/spike_channel3.py`. `POST /v1/search` "wireless headphones" → 20 real products (Philips, Sennheiser, Panasonic, JVC, Anker) with `images` on cdn.trychannel3.com, `offers`, `brands`, `ratings` |
| 5a | UCI Online Shoppers Purchasing Intention downloads and loads | **Pass** | 12,330 rows × 18 cols; `Revenue` True 1,908 / False 10,422. CC BY 4.0. DOI 10.24432/C5F88Q |
| 5b | Criteo Uplift v2.1 downloads and loads | **Pass** | 311 MB gz, columns f0–f11, treatment, conversion, visit, exposure. Official host `go.criteo.net` did not resolve from this machine; using the official Criteo mirror on Hugging Face (`criteo/criteo-uplift`, ungated). Licence CC BY-NC-SA 4.0 |

## Findings that change the plan

- **Pay Later is not free for merchants.** PayPal's current US fee page lists Pay Later at 4.99% + fixed fee against 3.49% + fixed fee for PayPal Checkout (+1.5 pp). UK: 3.9% vs 2.9% (+1.0 pp). See [EVIDENCE.md](EVIDENCE.md). The pitch line "can cost the merchant nothing extra" was wrong for the US and UK. **Decided 2026-11-10:** the pitch is now "Pay Later is the cheapest yes: a fraction of a discount, and only charged when the shopper uses it." The engine models Pay Later cost as `P(pays with Pay Later | converts) × 1.5% × order value` (US).
- **Criteo licence is non-commercial (CC BY-NC-SA 4.0).** Fine for an open-source research eval; the data is not redistributed in this repo, and no model trained on it ships in the product path. Uplift for the demo store comes from the simulator; Criteo is used only to validate the uplift-modelling method (Qini curve).
- **Old repo `wtp-dynamic-pricing-engine` has no licence file.** It's the same author's code, so reuse is fine, but anything copied gets re-licensed MIT here.
