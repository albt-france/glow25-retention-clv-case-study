-- 06_replenishment_timing.sql  (SIMULATED; jar duration from the public catalogue: 450 g / 15 g servings = 30 days)
-- When do one-off buyers of a 30-day product reorder, and when should the reminder go out?

-- output: reorder_gap_distribution
with gaps as (
    select o.customer_id, o.supply_days,
           date_diff('day', o.ts_berlin, lead(o.ts_berlin) over (partition by o.customer_id order by o.ts_utc)) as gap_days
    from fct_order o where not o.is_subscription)
select gap_days, count(*) as reorders
from gaps where supply_days = 30 and gap_days between 0 and 120
group by 1 order by 1;

-- output: reorder_gap_summary
with gaps as (
    select o.supply_days,
           date_diff('day', o.ts_berlin, lead(o.ts_berlin) over (partition by o.customer_id order by o.ts_utc)) as gap_days
    from fct_order o where not o.is_subscription)
select count(*) as reorders,
       quantile_cont(gap_days, 0.25) as p25, median(gap_days) as median_gap, quantile_cont(gap_days, 0.75) as p75,
       mode(gap_days) as mode_gap,
       avg((gap_days <= 21)::int) as share_reordering_before_day21,
       avg((gap_days <= 26)::int) as share_reordering_before_day26
from gaps where supply_days = 30 and gap_days between 0 and 120;

-- output: replenishment_j21_vs_j26
-- concurrent A/B, triggers 1 Feb - 31 May 2026: reminder at day 21 vs day 26 + "still have product?" branch (day 33)
with clicks as (
    select customer_id, entry_ts, count(*) filter (where clicked) / nullif(count(*) filter (where delivered), 0) as click_rate
    from email_events where flow_or_campaign = 'F4_replenishment' and sent group by 1, 2),
e as (
    select fo.*, c.click_rate
    from flow_outcome fo left join clicks c using (customer_id, entry_ts)
    where fo.flow = 'F4_replenishment' and fo.entry_ts between timestamp '2026-02-01' and timestamp '2026-05-31 23:59:59')
select case when holdout then 'holdout (no reminder)' else variant end as arm,
       count(*) as triggers, avg(converted::int) as repurchase_60d,
       1.96 * sqrt(avg(converted::int) * (1 - avg(converted::int)) / count(*)) as repurchase_ci95,
       avg(revenue_eur) as revenue_per_recipient_60d, avg(cm_eur) as cm_per_recipient_60d,
       avg(click_rate) as click_rate
from e group by 1 order by 1;
