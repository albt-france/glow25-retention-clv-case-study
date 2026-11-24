# Experiment playbook for lifecycle email

## 1. Default design: a permanent 10 % holdout per flow

- Every flow keeps 10 % of entrants who receive nothing from that flow (random, fixed per profile, never
  re-drawn). The holdout is what turns attributed revenue into incremental revenue.
- Message-level tests (timing, subject, offer) are A/B splits **inside** the treated 90 %.
- Campaigns: a 5-10 % holdout on the big seasonal sends (Black Friday, January) once per season.

## 2. Metrics

| Role | Metric | Why |
|---|---|---|
| Primary | Revenue per recipient over a fixed window after entry (all orders, not only attributed) | Captures orders that happen without a click |
| Decision | **Incremental contribution margin** per recipient (treated minus holdout) x recipients | A discount can raise revenue and lose margin |
| Guardrails | Unsubscribe rate, spam complaints, subscription cancellations | Long-term list health |
| Diagnostics | Click rate; opens only as a deliverability signal | Opens are inflated by machine opens (Apple Mail Privacy Protection): never a decision metric |

## 3. Sample size and minimum detectable effect

For revenue per recipient (mean, standard deviation s, n per arm), the minimum detectable effect at 5 %
significance and 80 % power is about `MDE = (1.96 + 0.84) x s x sqrt(1/n_t + 1/n_h)`.

With a 90/10 split the holdout is the bottleneck. Example (SIMULATED education flow): mean EUR 13.7 per recipient,
s about EUR 21, 74,000 treated and 8,200 holdout -> MDE about EUR 0.7 per recipient (about 5 %). The workbook
`excel/retention_economics.xlsx`, tab `Sample_Size`, computes this with `NORM.S.INV`.

Duration: until the holdout reaches the planned size **and** at least one full purchase cycle (35 days for a
30-day jar) has passed for the last entrants.

## 4. Decision rules

| Result (95 % interval on incremental CM per recipient) | Decision |
|---|---|
| Entirely above 0 and guardrails fine | **Scale** (keep the holdout) |
| Contains 0, point estimate positive | **Iterate**: change one thing, re-test |
| Contains 0, point estimate at or below 0 | **Stop** the message or offer, keep the content if it serves service |
| Entirely below 0 | **Stop** now |
| Guardrail breached (unsubscribes +30 % or more) | Stop, whatever the revenue |

Never: decide on open rate; read results before the planned date; compare pre/post periods across a season change
(January, Black Friday) without a holdout.

## 5. Seasonality traps

January lifts reorders of lapsed customers whatever we send (SIMULATED: +31 % vs December; PUBLIC DATA:
Wikipedia interest in collagen peaks every January). A flow launched on 2 January will always look like a
success in a pre/post chart. Only the holdout says whether it worked.

## 6. Read-out template (one per test)

1. Question and hypothesis. 2. Design (split, window, sample). 3. Result: incremental revenue and CM with 95 %
intervals, guardrails. 4. Decision (scale / iterate / stop / re-test date). 5. What it teaches the other teams.
