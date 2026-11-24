# Klaviyo flow specifications (8 flows)

Written in the usual Klaviyo vocabulary (trigger, trigger filter, flow filter, time delay, conditional split,
smart sending, profile property). Interface details are not claimed: the build would follow the account's own
setup. Event names (`Placed Order`, `Started Checkout`, ...) are the standard Shopify integration metrics; the
subscription events depend on the Recharge integration and must be checked in the account.

**Global rules for every flow**

- **Holdout**: 10 % of profiles entering the flow are held out permanently (random, per flow, never re-drawn).
- **Exclusions**: no win-back or promotional email to an active subscriber; no promotional email within 3 days
  after an order; maximum 3 marketing emails per profile per 7 days across flows and campaigns (campaigns take
  priority on launch days); smart sending on for marketing flows, off for transactional ones.
- **Consent**: email consent required; SMS only with SMS consent and never for the same message the same day.
- **Claims**: every email passes `src/claims_check.py`, then human review (claims_guardrail.md).
- **Stop rule**: a flow or message is paused if, after its planned sample, unsubscribes rise by more than 30 %
  relative to the holdout-period baseline or incremental CM per recipient is negative with 95 % confidence.

## F1 Welcome

| Item | Spec |
|---|---|
| Trigger | `Placed Order`, first order of the profile (list join at checkout) |
| Trigger filter | order count = 1 |
| Flow filter | has email consent; not in F1 in the last 30 days |
| Delays / messages | W1 within 1 h (welcome & first use), W2 day 2 (how to use it), W3 day 5 (brand story) |
| Branches | by first product: trial pack / full jar / cosmetic (copy changes, not the offer); market: FR uses the adapted version |
| Exclusion | none promotional in W1-W2; no discount in the welcome |
| KPI | revenue per recipient (14 days), unsubscribe rate per email |
| Holdout / stop | 10 %; stop W3 if its unsubscribe rate exceeds 0.8 % |

## F2 Post-purchase education

| Item | Spec |
|---|---|
| Trigger | `Placed Order`, first order, one-off |
| Flow filter | not an active subscriber (subscribers get F5) |
| Delays | days 3, 10, 17, 24, 31 |
| Branches | first product type (powder / sticks / ampoules / trial); opened E2 or not (shorter E3 for non-openers) |
| Exclusion | skip a message if the profile ordered in the last 3 days or received a campaign the same day |
| KPI | incremental 45-day revenue and CM vs holdout (not attributed revenue) |
| Holdout / stop | 10 %; SIMULATED read-out: about 22 % of attributed revenue is incremental -> cut to 3 emails, test content vs no email for E4-E5 |

## F3 Trial pack -> subscription

| Item | Spec |
|---|---|
| Trigger | `Placed Order` containing a 225 g trial pack (15 servings, not subscribable) |
| Flow filter | not subscribed; has not placed another order since the trigger |
| Delays | T1 day 4 (one-click question: easy / forgetting / taste), T2 day 9 (subscribe and save 15 %), T3 day 13 (last servings) |
| Branches | conditional split on the T1 answer (profile property): "forgetting" gets the habit tips, "taste" gets recipes, no offer pressure |
| Exclusion | exit on any order or subscription start |
| KPI | subscription starts within 30 days vs holdout; 90-day CM per entrant |
| Holdout / stop | 10 %; SIMULATED: +4 points of 30-day conversion vs holdout |

## F4 Replenishment (day 26 + branch)

| Item | Spec |
|---|---|
| Trigger | `Placed Order` of a 30-serving product (one-off) |
| Flow filter | no order since trigger; not an active subscriber |
| Delays | R1 day 26 ("about 4 servings left?"), R2 day 33 only for "I still have some" |
| Branches | R1 button "I still have some" sets a profile date -> R2; later: personal delay = customer's own median reorder gap minus 6 days |
| Exclusion | exit on order; skip if a campaign was sent in the last 24 h |
| KPI | 60-day repurchase, revenue and CM per trigger, vs holdout |
| Holdout / stop | 10 %; SIMULATED A/B: day 26 + branch 56.1 % vs day 21 51.5 % 60-day repurchase |

## F5 Subscription onboarding

| Item | Spec |
|---|---|
| Trigger | subscription created (Recharge event; name to check in the account) |
| Delays | S1 within 1 h (your plan, your next date), S2 day 5 (how to skip, swap, pause), S3 day 20 (next delivery reminder) |
| Branches | monthly vs every 3 months (copy); first subscription vs returning subscriber |
| Exclusion | no promotional campaigns during the first 21 days |
| KPI | churn before the 3rd charge, vs holdout |
| Holdout / stop | 10 % |

## F6 Cancel-save

| Item | Spec |
|---|---|
| Trigger | cancel intent in the customer portal (the portal shows skip / swap / pause first; the email follows up) |
| Flow filter | active subscriber; not a payment failure (dunning is separate) |
| Delays | X1 immediately; X2 day 2 only if the reason is "too expensive" |
| Branches | by cancel reason: too much product -> skip / pause; taste -> swap; too expensive -> slower rhythm or smaller format, no % discount |
| Exclusion | never more than one save attempt per subscription per 90 days; the cancel link is always visible |
| KPI | save rate (no cancellation within 14 days) and 90-day CM of saved subscribers |
| Holdout / stop | 10 % see the plain cancel page; SIMULATED save rate about 30 % vs 8 % |

## F7 Win-back

| Item | Spec |
|---|---|
| Trigger | 90 days without an order (date property, daily) |
| Flow filter | no active subscription; not in F7 in the last 180 days |
| Delays | B1 day 0 (what is new), B2 day 10 (best-sellers, reviews), B3 day 25 (small offer, 10 %, one use) |
| Branches | past subscriber vs one-off buyer; cancel reason if known |
| Exclusion | exit on order; never to customers who complained in the last 90 days |
| KPI | 30-day reorder vs holdout, incremental CM |
| Holdout / stop | 10 %; SIMULATED: launched 2 January 2026, January reorders up for both groups (seasonality) -> no effect proven, re-test from March |

## F8 VIP / loyalty

| Item | Spec |
|---|---|
| Trigger | reached the top tier (Gold: loyalty member with EUR 300 lifetime spend) |
| Delays | V1 day 0 (welcome to Gold), then launch early access 48 h before each launch |
| Branches | subscriber vs one-off |
| Exclusion | early access is never discounted |
| KPI | matched reorder lift (same cohort, market and prior orders), CM per member |
| Holdout / stop | 10 %; SIMULATED early access: no measurable lift yet on small samples, no margin cost |

A schema of F4 is in [flow_f4_replenishment.svg](flow_f4_replenishment.svg).
