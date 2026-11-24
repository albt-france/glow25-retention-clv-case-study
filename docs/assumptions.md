# Assumptions

## Public facts used for calibration (PUBLIC DATA, read 2026-11-24)

- Product types and prices: Glow25 catalogue (29 products via `/products/<handle>.js`): powder EUR 29.99, Plus
  EUR 39.99, Intensiv sticks EUR 49.99, drink ampoules EUR 59.99, trial packs EUR 14.99 / EUR 19.99, bundles
  EUR 27.99-89.99.
- Subscription plans: 8 products, each with "Monatliche Lieferung" (-15 %) and "Lieferung alle 3 Monate" (-25 %).
- Jar duration: trial pack label 225 g = 15 servings -> 15 g per serving; 450 g jar (variant weight) -> 30 days.
  The 450 g figure is the variant weight in the catalogue and may include packaging: **assumption**.
- Market weights: Eurostat isoc_ec_ibgs 2024 (women 25-54), supplements x beauty online shares, times a rough
  market-size factor and a home-market premium for DE and AT (**assumption**); GB uses the DE value (no 2024 EU value).
- Seasonality: monthly Wikipedia pageviews of the collagen article in DE, FR, IT, NL, ES (Nov 2023 - Oct 2026).
- Reorder curve shape: inspired by the UCI Online Retail II repeat-purchase pattern (proportions only).

## Simulation assumptions (SIMULATED, Brand G)

| Item | Value | Note |
|---|---|---|
| Period | 2024-11-01 to 2026-10-31 | timestamps UTC, reports Europe/Berlin |
| New customers | about 120,000 (+2,300 duplicate profiles) | monthly volume follows the seasonality index, +30 % in November |
| Amounts | net of VAT | |
| Cost of goods | about 22-25 % of list price (e.g. EUR 6.90 for a EUR 29.99 jar) | assumption |
| Shipping cost (paid by the brand) | DE 4.20, AT 5.40, FR 5.90, BE / NL 5.60, IT / ES 6.20, GB 7.80 EUR; +4.00 for a 3-jar parcel | assumption |
| Payment fee | 1.9 % + EUR 0.25 | assumption |
| Refunds | 2.5 % of one-off orders, 1 % of subscription orders | assumption |
| Every-3-months plan | 3 jars per delivery at -25 % | the public plan name only says "every 3 months" |
| Email consent | 82 % of customers; SMS 28 % | assumption |
| Machine opens | about a third of profiles use Apple Mail; recorded from September 2025 | assumption |
| Genuine open rate | about 40 %; click rate 3-8 % per email depending on flow | assumption |
| Attribution | last touch: click within 5 days, else open within 1 day | Klaviyo-style default |
| Holdout | 10 % per flow, independent draw per flow | |
| Subscription price increase | +10 % on 2026-04-01 | SIMULATED event |

The eight planted events and their exact parameters are listed in the PDF (page 6) as "planted vs found"; the
file that held them was used only to score the analysis and is not published.
