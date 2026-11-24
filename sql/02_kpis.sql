-- 02_kpis.sql  (SIMULATED) - the retention KPIs defined in docs/kpi_dictionary.md
-- Data end: 2026-10-31. A rate over N days only uses customers whose first order is at least N days old.

-- output: kpi_repurchase
with second as (
    select customer_id, min(ts_utc) filter (where order_seq = 2) as second_ts from fct_order group by customer_id
),
base as (
    select f.*, s.second_ts, date_diff('day', f.first_ts, s.second_ts) as days_to_second
    from dim_customer_first f join second s using (customer_id)
),
windows as (select unnest([30, 60, 90, 180, 365]) as n_days)
select 'all' as segment, w.n_days,
       count(*) filter (where b.first_ts <= timestamp '2026-10-31' - to_days(w.n_days)) as customers,
       avg(case when b.days_to_second <= w.n_days then 1 else 0 end)
           filter (where b.first_ts <= timestamp '2026-10-31' - to_days(w.n_days)) as repurchase_rate
from base b cross join windows w group by w.n_days
union all
select 'first order: ' || case when b.subscribed_at_first_order then 'subscription'
                               when b.first_product_type in ('trial', 'bundle') then 'trial pack / bundle'
                               else 'one-off ' || b.first_product_type end, w.n_days,
       count(*) filter (where b.first_ts <= timestamp '2026-10-31' - to_days(w.n_days)),
       avg(case when b.days_to_second <= w.n_days then 1 else 0 end)
           filter (where b.first_ts <= timestamp '2026-10-31' - to_days(w.n_days))
from base b cross join windows w group by all
order by segment, n_days;

-- output: kpi_orders_per_customer
select f.market,
       count(*) as customers,
       avg(n.orders_365) as orders_per_customer_365d,
       avg(n.cm_365) as cm_per_customer_365d
from dim_customer_first f
join (
    select o.customer_id, count(*) as orders_365, sum(o.cm_eur) as cm_365
    from fct_order o join dim_customer_first f using (customer_id)
    where o.ts_utc < f.first_ts + interval 365 day
    group by o.customer_id
) n using (customer_id)
where f.first_ts <= timestamp '2025-10-31'
group by rollup (f.market) order by customers desc;

-- output: kpi_email_by_flow
-- Klaviyo-style revenue per recipient = attributed revenue / delivered. Open rates shown with and without machine (MPP) opens.
with ev as (
    select flow_or_campaign,
           count(*) filter (where delivered) as delivered,
           count(*) filter (where opened) as opens,
           count(*) filter (where opened and not mpp_flag) as human_opens,
           count(*) filter (where clicked) as clicks,
           count(*) filter (where unsubscribed) as unsubs
    from email_events group by 1),
att as (select flow_or_campaign, sum(attributed_revenue_eur) as attributed_revenue_eur, count(*) as attributed_orders
        from attributed_orders group by 1)
select ev.flow_or_campaign, delivered, opens / delivered as open_rate, human_opens / delivered as open_rate_excl_mpp,
       clicks / delivered as click_rate, unsubs / delivered as unsubscribe_rate,
       coalesce(attributed_revenue_eur, 0) as attributed_revenue_eur, coalesce(attributed_orders, 0) as attributed_orders,
       coalesce(attributed_revenue_eur, 0) / delivered as revenue_per_recipient_eur
from ev left join att using (flow_or_campaign)
where delivered > 0
order by attributed_revenue_eur desc;

-- output: kpi_subscription_churn_monthly
with months as (select unnest(generate_series(date '2025-01-01', date '2026-10-01', interval 1 month))::date as m),
act as (
    select m.m,
           count(*) filter (where s.created < m.m and (s.cancelled is null or s.cancelled >= m.m)) as active_start,
           count(*) filter (where s.created < m.m and s.cancelled >= m.m and s.cancelled < m.m + interval 1 month) as cancellations
    from months m cross join fct_subscription s group by m.m),
sk as (select date_trunc('month', scheduled_date)::date as m, count(*) as skipped_charges from fct_charge where is_skip group by 1)
select a.m as month, a.active_start, a.cancellations, coalesce(sk.skipped_charges, 0) as skipped_charges,
       a.cancellations / a.active_start as churn_rate,
       (a.cancellations + coalesce(sk.skipped_charges, 0)) / a.active_start as naive_churn_rate_skips_counted
from act a left join sk using (m) order by month;

-- output: kpi_monthly_overview
select order_month as month,
       count(*) as orders,
       count(*) filter (where order_seq = 1) as new_customers,
       count(*) filter (where is_subscription) as subscription_orders,
       sum(net_revenue_eur) as net_revenue_eur,
       sum(cm_eur) as contribution_margin_eur,
       sum(cm_eur) / sum(net_revenue_eur) as cm_rate
from fct_order group by 1 order by 1;
