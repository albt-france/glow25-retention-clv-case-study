# Retention strategy: the lifecycle as one system

Scope: a collagen D2C brand with subscriptions (Glow25's public offer: 8 subscribable products, -15 % monthly or
-25 % every 3 months; 225 g trial packs that cannot be subscribed). Every number below marked SIMULATED comes from
the fictional "Brand G" data of this case study (seed 42), never from Glow25.

## 1. Lifecycle map, one KPI and one owner per stage

| Stage | What the customer needs | Main flows / levers | KPI (definition in kpi_dictionary.md) | Owner |
|---|---|---|---|---|
| First order | Confidence the order is right, a simple first use | Welcome (F1), order emails | 14-day revenue per recipient; unsubscribe rate | Retention & CLV Operator |
| Education | Turn a product into a habit in the first 30 days | Post-purchase education (F2) | Incremental 45-day revenue vs holdout | Retention & CLV Operator, with Creative |
| Trial -> full size | A reason to continue when the 15 servings run out | Trial pack -> subscription (F3) | Subscription starts within 30 days, vs holdout | Retention & CLV Operator |
| Replenishment | A reminder when the jar is nearly empty, not before | Replenishment day 26 + branch (F4) | 60-day repurchase rate, incremental | Retention & CLV Operator |
| Subscription | Control: skip, swap, pause, change rhythm | Onboarding (F5), cancel-save (F6), customer portal | Monthly churn (skips excluded); save rate | Retention & CLV Operator, with CX |
| Loyalty / VIP | Recognition, early access, no discount spiral | VIP / loyalty (F8), launch early access | Matched reorder lift; CM per member | Retention & CLV Operator, with Product |
| Win-back | A real reason to come back, sent when it can still work | Win-back (F7), seasonal campaigns | Incremental 30-day reorder vs holdout; CM | Retention & CLV Operator |
| Measurement | Decisions on margin, not on attributed revenue | 10 % holdout per flow, weekly update | Incremental contribution margin per flow | Retention & CLV Operator, with Analytics |

## 2. What the data says (SIMULATED unless stated)

- **Attributed revenue overstates value.** The education flow claims about EUR 302k of last-touch revenue, but its
  holdout shows that only about 22 % of it is incremental: most clickers would have reordered anyway. The
  replenishment flow is far more incremental (about 74 %, with a wide interval).
- **Timing beats volume.** The median one-off reorder comes about 34 days after the previous order (mode 32);
  only 1.6 % reorder before day 21. A day-26 reminder with a "still have some?" branch beat day 21 by
  +4.6 points of 60-day repurchase in a concurrent A/B test.
- **The every-3-months plan keeps people, the monthly plan earns more.** 12-month retention 59 % vs 40 %, but
  12-month CM-CLV is about 6 % lower (deeper discount, heavier parcel, more skips from stock build-up).
- **Discounts to win back price-sensitive cancellers lose money.** A -30 % comeback offer brought back 18 % of
  "too expensive" cancellers (13 % without the offer) and earned less contribution margin per recipient over
  6 months than the holdout.
- **January lifts everything.** Lapsed customers reorder about 31 % more in January than in December, with or
  without the new win-back flow (PUBLIC DATA: Wikipedia interest in collagen peaks in January in all five
  languages checked).

## 3. Five priorities, in order

1. **Measure every flow against a permanent 10 % holdout and report incremental contribution margin** next to
   attributed revenue (playbook: experiment_playbook.md). Without it, budget and attention go to the flows that
   claim the most, not to the ones that earn the most.
2. **Move the replenishment reminder to day 26 with a branch**, personalised later by each customer's own reorder
   gap. Cheapest, clearest win.
3. **Make the trial pack a bridge to the subscription** (the trial pack is not subscribable): a 3-email flow
   with a reply-button question on day 4, the subscription offer on day 9, before the 15 servings run out.
4. **Save subscriptions with control, not with discounts**: skip / swap / pause before cancel (save rate about
   30 % vs 8 % on a plain cancel page, SIMULATED), monthly plan with skip shown first, no -30 % comeback
   offers. Test an "upgrade pack" for price-sensitive customers instead.
5. **Localise, do not translate**: France buys beauty online far more than supplements (Eurostat 2024, women
   25-54: 29.1 % vs 11.8 %), so FR flows lead with the beauty ritual. One brand voice, adapted stories and offers
   per market (localisation_playbook.md).

## 4. What is shared, with whom

| Team | What retention sends them each week | What retention needs from them |
|---|---|---|
| Acquisition | CM-CLV at 3 / 6 / 12 months by first product and channel (influencer cohorts are worth less) | Planned launches and promotions 6 weeks ahead |
| Creative | Winning angles per market, with the read-out | Visual systems that work in email (dark mode, mobile) |
| Customer service | Top cancel reasons, saved / not saved | Verbatims on taste, delivery, price |
| Product | Swap flows, demand for formats (trial, 3 jars) | Stock and launch dates for early access |
| Analytics | Holdout read-outs, data issues found | Clean order / subscription data, shared definitions |
