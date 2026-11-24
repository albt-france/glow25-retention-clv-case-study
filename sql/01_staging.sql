-- 01_staging.sql  (SIMULATED data, Brand G)
-- Fixes the three data issues before any KPI (see docs/data_issues_log.md):
--   1. duplicate profiles: the same email_hash under two customer ids (DE and AT) -> one canonical customer;
--   2. skipped subscription charges are NOT cancellations -> kept in their own status;
--   3. timestamps are stored in UTC -> converted to Europe/Berlin before any day or month is computed.

create or replace table customer_map as
with ranked as (
    select customer_id, email_hash, first_order_ts,
           first_value(customer_id) over (partition by email_hash order by first_order_ts, customer_id) as canonical_id
    from customers
)
select customer_id, canonical_id, customer_id <> canonical_id as is_duplicate
from ranked;

create or replace table dim_customer as
select c.customer_id, c.market, c.acquisition_channel, c.consent_email, c.consent_sms,
       c.loyalty_member, c.loyalty_tier, c.loyalty_joined_ts
from customers c
join customer_map m using (customer_id)
where not m.is_duplicate;

create or replace table fct_order as
with o as (
    select o.order_id,
           m.canonical_id                                                    as customer_id,
           o.ts_utc,
           (o.ts_utc at time zone 'UTC') at time zone 'Europe/Berlin'        as ts_berlin,
           o.is_subscription, o.subscription_id, o.campaign_code,
           o.gross_eur, o.discount_eur, o.shipping_eur, o.cogs_eur, o.payment_fee_eur, o.refund_eur,
           o.gross_eur - o.discount_eur                                      as net_revenue_eur,
           o.gross_eur - o.discount_eur - o.cogs_eur - o.shipping_eur - o.payment_fee_eur - o.refund_eur as cm_eur
    from orders o
    join customer_map m using (customer_id)
),
main_line as (
    select l.order_id, p.type as product_type, p.product_id, p.supply_days
    from order_lines l join products p using (product_id)
    where l.line_no = 1
)
select o.*, d.market, d.acquisition_channel,
       cast(o.ts_berlin as date)                                          as order_date,
       date_trunc('month', o.ts_berlin)::date                             as order_month,
       ml.product_id, ml.product_type, ml.supply_days,
       row_number() over (partition by o.customer_id order by o.ts_utc, o.order_id) as order_seq
from o
join dim_customer d using (customer_id)
join main_line ml using (order_id);

create or replace table dim_customer_first as
select customer_id, market, acquisition_channel,
       ts_utc as first_ts, order_month as cohort_month, product_type as first_product_type,
       product_id as first_product_id, is_subscription as subscribed_at_first_order
from fct_order where order_seq = 1;

create or replace table fct_subscription as
select s.subscription_id, m.canonical_id as customer_id, s.product, s.interval, s.discount,
       s.created, s.cancelled, s.cancel_reason, s.skips, s.swaps, s.origin,
       date_trunc('month', (s.created at time zone 'UTC') at time zone 'Europe/Berlin')::date as created_month
from subscriptions s
join customer_map m using (customer_id);

-- charges: success / retried / failed / skipped. A skip is a paused delivery, not a churned customer.
create or replace table fct_charge as
select c.*, s.customer_id, s.interval, c.status = 'skipped' as is_skip
from charges c join fct_subscription s using (subscription_id);

-- output: data_quality_summary
with dup as (select count(*) as n from customer_map where is_duplicate),
     moved as (select count(*) as n from orders o join customer_map m using (customer_id) where m.is_duplicate),
     slip as (
        select count(*) filter (where date_trunc('month', ts_utc) <> date_trunc('month', ts_berlin)) as n_slip,
               count(*) filter (where is_subscription) as n_sub
        from fct_order where is_subscription),
     months as (select unnest(generate_series(date '2025-01-01', date '2026-09-01', interval 1 month))::date as m),
     churn as (
        select m.m,
               count(distinct s.subscription_id) filter (where s.created < m.m and (s.cancelled is null or s.cancelled >= m.m)) as active,
               count(distinct s.subscription_id) filter (where s.cancelled >= m.m and s.cancelled < m.m + interval 1 month
                                                          and s.created < m.m) as cancels
        from months m cross join fct_subscription s group by m.m),
     skips as (
        select date_trunc('month', scheduled_date)::date as m, count(*) as skips
        from fct_charge where is_skip group by 1),
     rate as (
        select avg(c.cancels / c.active) as true_churn, avg((c.cancels + coalesce(k.skips, 0)) / c.active) as naive_churn
        from churn c left join skips k using (m))
select 'duplicate profiles (same email_hash)' as check_name, (select n from dup)::double as value
union all select 'orders sitting on a duplicate profile', (select n from moved)
union all select 'subscription orders whose UTC month differs from the Berlin month', (select n_slip from slip)
union all select 'share of subscription orders that slip month', (select n_slip / n_sub from slip)
union all select 'monthly subscription churn, skipped counted as cancelled (naive)', (select naive_churn from rate)
union all select 'monthly subscription churn, cancellations only (correct)', (select true_churn from rate);
