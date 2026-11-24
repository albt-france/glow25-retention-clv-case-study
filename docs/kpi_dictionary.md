# KPI dictionary

Times are converted from UTC to Europe/Berlin before any day or month is computed. Customers are de-duplicated on
the email hash first (one person = one customer). Amounts are net of VAT.

| KPI | Exact definition | SQL |
|---|---|---|
| Repurchase rate N days | Share of customers whose 2nd order is within N days of the 1st, among customers whose 1st order is at least N days before the data end | 02_kpis.sql |
| Orders per customer (365 d) | Orders in the 365 days from the first order / customers acquired at least 365 days ago | 02_kpis.sql |
| Contribution margin (CM) per order | Gross - discounts - cost of goods - shipping cost - payment fees - refunds | 04_contribution_margin.sql |
| CM-CLV (k months) | Cumulative CM per customer of a cohort, from the month of the first order to month k-1 | 03_cohorts.sql |
| Revenue per recipient (RPR), attributed | Attributed revenue / delivered emails (the ESP view) | 02_kpis.sql |
| Revenue per recipient, incremental | Net revenue per entrant in a fixed window, treated minus holdout | 05_flow_holdout_readout.sql |
| Attributed revenue | Orders after a click within 5 days, or an open within 1 day, last touch (Klaviyo-style) | attributed_orders |
| Incremental revenue | (RPR treated - RPR holdout) x treated entrants | 05_flow_holdout_readout.sql |
| Incremental share | Incremental revenue / attributed revenue of the same entrants | 05_flow_holdout_readout.sql |
| Subscription churn rate (monthly) | Cancellations in the month / subscriptions active at the start of the month. **Skipped charges are not cancellations.** | 01_staging.sql, 02_kpis.sql |
| Subscription retention 12 m | Share of subscriptions started in a cohort still active 365 days later | 07_subscription_economics.sql |
| Skip rate | Skipped charges / scheduled charges | 07_subscription_economics.sql |
| Save rate | Cancel intents not followed by a cancellation within 14 days / cancel intents | 07_subscription_economics.sql |
| Unsubscribe rate | Unsubscribes / delivered, per email | 02_kpis.sql |
| Open rate (human) | Opens without the machine-open flag / delivered (diagnostic only) | 10_mpp_opens.sql |
| Click rate | Clicks / delivered | 10_mpp_opens.sql |
| Loyalty lift (matched) | Reorder within 180 days, members vs non-members of the same cohort quarter, market and number of prior orders, weighted by members | 09_loyalty_selection_bias.sql |
