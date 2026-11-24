-- 07_subscription_economics.sql  (SIMULATED; discounts -15 % monthly and -25 % every 3 months are Glow25's public plans)
-- Monthly vs every-3-months, skip / swap / save, price increase, and the -30 % win-back offer.

-- output: sub_plan_economics
-- subscriptions started Nov 2024 - Oct 2025 (12 months observable), standard offer only
with s as (
    select * from fct_subscription
    where created < timestamp '2025-11-01' and origin in ('first_order', 'reorder_conversion', 'trial_flow')),
cm as (
    select s.subscription_id, sum(o.cm_eur) as cm_12m, sum(o.net_revenue_eur) as revenue_12m, count(*) as charges_12m
    from s join fct_order o using (subscription_id)
    where o.ts_utc < s.created + interval 365 day group by 1),
sk as (
    select s.subscription_id, count(*) filter (where c.is_skip) as skips_12m, count(*) as scheduled_12m
    from s join fct_charge c using (subscription_id)
    where c.scheduled_date < cast(s.created + interval 365 day as date) group by 1)
select s.interval, count(*) as subscriptions,
       avg((s.cancelled is null or s.cancelled >= s.created + interval 365 day)::int) as retention_12m,
       avg(cm.cm_12m) as cm_clv_12m_eur, avg(cm.revenue_12m) as revenue_12m_eur, avg(cm.charges_12m) as paid_charges_12m,
       avg(cm.cm_12m / cm.charges_12m) as cm_per_paid_charge,
       sum(sk.skips_12m) / sum(sk.scheduled_12m) as skip_rate_per_scheduled_charge,
       avg(s.swaps) as swaps_per_sub
from s join cm using (subscription_id) join sk using (subscription_id)
group by 1 order by 1;

-- output: sub_retention_curve
with s as (select * from fct_subscription
           where created < timestamp '2025-11-01' and origin in ('first_order', 'reorder_conversion', 'trial_flow')),
d as (select unnest(range(0, 391, 30)) as day)
select s.interval, d.day,
       avg((s.cancelled is null or s.cancelled >= s.created + to_days(d.day))::int) as still_active
from s cross join d group by 1, 2 order by 1, 2;

-- output: sub_cancel_reasons
select case when created_month < date '2026-04-01' then 'before' else 'after' end as period_created,
       cancel_reason, count(*) as cancellations
from fct_subscription where cancelled is not null group by all order by 1, 3 desc;

-- output: cancel_save_readout
-- cancel intent (portal) -> skip / swap / pause offer; saved = no cancellation in the 14 days after the intent
with e as (
    select fe.customer_id, fe.entry_ts, fe.holdout,
           exists (select 1 from fct_subscription s where s.customer_id = fe.customer_id
                   and s.cancelled > fe.entry_ts and s.cancelled <= fe.entry_ts + interval 14 day) as cancelled_14d
    from flow_entries fe where fe.flow = 'F6_cancel_save')
select case when holdout then 'holdout (plain cancel page)' else 'skip / swap / pause offered' end as arm,
       count(*) as cancel_intents, 1 - avg(cancelled_14d::int) as save_rate,
       1.96 * sqrt(avg(cancelled_14d::int) * (1 - avg(cancelled_14d::int)) / count(*)) as save_rate_ci95
from e group by 1 order by 1;

-- output: price_increase_too_expensive
-- "too expensive" cancellations per 1,000 active subscriptions per month, 6 months before vs after 1 April 2026
with months as (select unnest(generate_series(date '2025-10-01', date '2026-09-01', interval 1 month))::date as m),
mk as (select unnest(['DE', 'FR', 'IT', 'other']) as mkt),
base as (
    select s.*, case when d.market in ('DE', 'FR', 'IT') then d.market else 'other' end as mkt
    from fct_subscription s join dim_customer d using (customer_id)),
x as (
    select m.m, b.mkt,
           count(*) filter (where b.created < m.m and (b.cancelled is null or b.cancelled >= m.m)) as active,
           count(*) filter (where b.cancel_reason = 'too_expensive' and b.cancelled >= m.m and b.cancelled < m.m + interval 1 month) as too_expensive
    from months m cross join base b group by 1, 2)
select mkt as market, case when m < date '2026-04-01' then 'Oct 2025 - Mar 2026 (before)' else 'Apr - Sep 2026 (after +10 %)' end as period,
       sum(too_expensive) as too_expensive_cancellations, sum(active) as active_sub_months,
       1000.0 * sum(too_expensive) / sum(active) as per_1000_active
from x group by 1, 2 order by 1, 2 desc;

-- output: winback30_readout
-- standing -30 % comeback offer to "too expensive" cancellers; offers sent up to 30 April 2026 (6 months observable)
with w as (
    select m.canonical_id as customer_id, w.offer_ts, w.holdout_flag
    from winback_offers w join customer_map m using (customer_id)
    where w.offer_ts <= timestamp '2026-04-30 23:59:59'),
r as (
    select w.*,
           exists (select 1 from fct_subscription s where s.customer_id = w.customer_id
                   and s.created > w.offer_ts and s.created <= w.offer_ts + interval 30 day) as returned,
           coalesce((select sum(o.cm_eur) from fct_order o where o.customer_id = w.customer_id
                     and o.ts_utc > w.offer_ts and o.ts_utc <= w.offer_ts + interval 180 day), 0) as cm_180d,
           coalesce((select sum(o.net_revenue_eur) from fct_order o where o.customer_id = w.customer_id
                     and o.ts_utc > w.offer_ts and o.ts_utc <= w.offer_ts + interval 180 day), 0) as revenue_180d
    from w)
select case when holdout_flag then 'holdout (no offer)' else '-30 % offer' end as arm,
       count(*) as recipients, avg(returned::int) as return_rate,
       avg(revenue_180d) as revenue_per_recipient_180d, avg(cm_180d) as cm_per_recipient_180d,
       1.96 * sqrt(var_samp(cm_180d) / count(*)) as cm_ci95
from r group by 1 order by 1;
