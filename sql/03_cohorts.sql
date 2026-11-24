-- 03_cohorts.sql  (SIMULATED) - monthly cohorts: who comes back, and what they are worth in contribution margin
-- month_index 0 = month of the first order (Berlin time). CM-CLV = cumulative contribution margin per customer.

create or replace table cohort_activity as
select f.customer_id, f.cohort_month, f.market, f.acquisition_channel,
       case when f.subscribed_at_first_order then 'subscription'
            when f.first_product_type in ('trial', 'bundle') then 'trial pack / bundle'
            when f.first_product_type = 'cosmetic' then 'cosmetic'
            else 'one-off supplement' end as first_order_type,
       date_diff('month', f.cohort_month, o.order_month) as month_index,
       count(*) as orders, sum(o.cm_eur) as cm_eur, sum(o.net_revenue_eur) as revenue_eur
from dim_customer_first f join fct_order o using (customer_id)
group by all;

-- output: cohort_retention
-- share of the cohort with at least one order in month k, and cumulative CM per customer at month k
with sizes as (select cohort_month, count(*) as customers from dim_customer_first group by 1),
grid as (
    select s.cohort_month, s.customers, k.month_index
    from sizes s cross join (select unnest(range(0, 24)) as month_index) k
    where s.cohort_month + to_months(k.month_index) <= date '2026-10-01'),
act as (
    select cohort_month, month_index, count(distinct customer_id) as active, sum(cm_eur) as cm_eur
    from cohort_activity group by 1, 2)
select g.cohort_month, g.month_index, g.customers,
       coalesce(a.active, 0) / g.customers as active_share,
       sum(coalesce(a.cm_eur, 0)) over (partition by g.cohort_month order by g.month_index) / g.customers as cm_clv_eur
from grid g left join act a using (cohort_month, month_index)
order by 1, 2;

-- output: cohort_cmclv_by_segment
-- CM-CLV at 3, 6 and 12 months for cohorts with 12 full months observed (first order Nov 2024 - Oct 2025)
with seg as (
    select customer_id, 'first order type' as dimension, first_order_type as segment from cohort_activity
    union select customer_id, 'market', market from cohort_activity
    union select customer_id, 'acquisition channel', acquisition_channel from cohort_activity),
eligible as (select customer_id from dim_customer_first where cohort_month <= date '2025-10-01')
select s.dimension, s.segment, count(distinct s.customer_id) as customers,
       sum(a.cm_eur) filter (where a.month_index <= 2) / count(distinct s.customer_id) as cm_clv_3m,
       sum(a.cm_eur) filter (where a.month_index <= 5) / count(distinct s.customer_id) as cm_clv_6m,
       sum(a.cm_eur) filter (where a.month_index <= 11) / count(distinct s.customer_id) as cm_clv_12m,
       count(distinct a.customer_id) filter (where a.month_index between 1 and 11 and a.orders > 0) / count(distinct s.customer_id)
           as returned_within_12m
from seg s join eligible e using (customer_id)
join cohort_activity a using (customer_id)
group by 1, 2 order by 1, cm_clv_12m desc;
