-- 08_january_false_signal.sql  (SIMULATED)
-- The win-back flow went live on 2 January 2026 and January reorders of lapsed customers jumped.
-- Was it the flow? Compare with its own 10 % holdout, and with December (no flow).

-- output: lapsed_reactivation_by_month
-- lapsed = no order in the 90 days before the month and no active subscription; outcome = an order during the month
with months as (select unnest(generate_series(date '2025-09-01', date '2026-06-01', interval 1 month))::date as m),
last_before as (
    select m.m, o.customer_id, max(o.ts_berlin) as last_order
    from months m join fct_order o on o.ts_berlin < m.m group by 1, 2),
active_sub as (
    select distinct m.m, s.customer_id from months m join fct_subscription s
      on s.created < m.m and (s.cancelled is null or s.cancelled >= m.m)),
lapsed as (
    select l.m, l.customer_id from last_before l
    left join active_sub a using (m, customer_id)
    where l.last_order < l.m - interval 90 day and a.customer_id is null),
out as (
    select l.m, l.customer_id,
           exists (select 1 from fct_order o where o.customer_id = l.customer_id and o.ts_berlin >= l.m
                   and o.ts_berlin < l.m + interval 1 month) as reordered
    from lapsed l)
select m as month, count(*) as lapsed_customers, avg(reordered::int) as reorder_rate
from out group by 1 order by 1;

-- output: winback_january_readout
-- entries of January 2026 vs entries of later months: treated vs holdout, order within 30 days of entry
select date_trunc('month', entry_ts)::date as entry_month,
       count(*) filter (where not holdout) as treated, count(*) filter (where holdout) as holdout,
       avg(converted::int) filter (where not holdout) as conv_treated,
       avg(converted::int) filter (where holdout) as conv_holdout,
       avg(converted::int) filter (where not holdout) - avg(converted::int) filter (where holdout) as diff_pts,
       1.96 * sqrt(avg(converted::int) filter (where not holdout) * (1 - avg(converted::int) filter (where not holdout)) / count(*) filter (where not holdout)
                 + avg(converted::int) filter (where holdout) * (1 - avg(converted::int) filter (where holdout)) / count(*) filter (where holdout)) as diff_ci95
from flow_outcome where flow = 'F7_winback'
group by 1 order by 1;
