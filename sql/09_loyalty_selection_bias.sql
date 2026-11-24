-- 09_loyalty_selection_bias.sql  (SIMULATED)
-- Do loyalty members reorder more because of the programme, or because heavy buyers join it?
-- Unit: a one-off order between Jan 2025 and Apr 2026. Outcome: another order within 180 days.

create or replace table loyalty_anchor as
select o.order_id, o.customer_id, o.ts_utc, o.market, f.cohort_month,
       date_trunc('quarter', f.cohort_month)::date as cohort_quarter,
       least(o.order_seq - 1, 6) as prior_orders_bucket,
       (d.loyalty_joined_ts is not null and d.loyalty_joined_ts <= o.ts_utc) as member_at_order,
       exists (select 1 from fct_order n where n.customer_id = o.customer_id and n.ts_utc > o.ts_utc
               and n.ts_utc <= o.ts_utc + interval 180 day) as reorder_180d
from fct_order o
join dim_customer d using (customer_id)
join dim_customer_first f using (customer_id)
where not o.is_subscription and o.ts_utc between timestamp '2025-01-01' and timestamp '2026-04-30 23:59:59';

-- output: loyalty_naive_vs_matched
with naive as (
    select avg(reorder_180d::int) filter (where member_at_order) as r_member,
           avg(reorder_180d::int) filter (where not member_at_order) as r_non
    from loyalty_anchor),
strata as (
    select cohort_quarter, market, prior_orders_bucket,
           count(*) filter (where member_at_order) as n_m, count(*) filter (where not member_at_order) as n_n,
           avg(reorder_180d::int) filter (where member_at_order) as r_m,
           avg(reorder_180d::int) filter (where not member_at_order) as r_n
    from loyalty_anchor group by all),
matched as (
    select sum(n_m * r_m) / sum(n_m) as r_member, sum(n_m * r_n) / sum(n_m) as r_non, sum(n_m) as n_members_matched
    from strata where n_m > 0 and n_n >= 20)
select 'naive: members vs everyone else' as comparison, r_member, r_non, r_member / r_non - 1 as relative_lift, null as members_used
from naive
union all
select 'matched: same cohort quarter, market and number of prior orders', r_member, r_non, r_member / r_non - 1, n_members_matched
from matched;

-- output: loyalty_mix
select prior_orders_bucket, member_at_order, count(*) as anchor_orders, avg(reorder_180d::int) as reorder_180d
from loyalty_anchor group by 1, 2 order by 1, 2;
