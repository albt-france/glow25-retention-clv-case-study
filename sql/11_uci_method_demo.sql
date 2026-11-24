-- 11_uci_method_demo.sql  (PUBLIC DATA: UCI Online Retail II, a UK online retailer 2009-2011, CC BY 4.0)
-- Method demo on real transactions of ANOTHER business (gifts and homewares, many wholesale buyers).
-- These are not Glow25 customers and say nothing about collagen buyers. Invoice level, returns and
-- missing customer ids already removed (data/public/uci_cleaning_log.csv). Data end: 2011-12-09.

create or replace table uci_inv as
select invoice, customer_id, invoice_ts, amount_gbp,
       date_trunc('month', invoice_ts)::date as inv_month,
       row_number() over (partition by customer_id order by invoice_ts, invoice) as seq,
       min(invoice_ts) over (partition by customer_id) as first_ts
from uci_invoices;

-- output: uci_cohort_retention
with c as (select customer_id, date_trunc('month', first_ts)::date as cohort from uci_inv where seq = 1),
sizes as (select cohort, count(*) as customers from c group by 1),
act as (select c.cohort, date_diff('month', c.cohort, i.inv_month) as month_index, count(distinct i.customer_id) as active,
               sum(i.amount_gbp) as revenue
        from c join uci_inv i using (customer_id) group by 1, 2)
select a.cohort, a.month_index, s.customers, a.active / s.customers as active_share,
       sum(a.revenue) over (partition by a.cohort order by a.month_index) / s.customers as cum_revenue_per_customer_gbp
from act a join sizes s using (cohort)
where a.cohort + to_months(a.month_index) <= date '2011-11-01'
order by 1, 2;

-- output: uci_repurchase
with second as (select customer_id, min(first_ts) as first_ts, min(invoice_ts) filter (where seq = 2) as second_ts
                from uci_inv group by 1),
w as (select unnest([30, 60, 90, 180, 365]) as n_days)
select w.n_days,
       count(*) filter (where s.first_ts <= timestamp '2011-12-09' - to_days(w.n_days)) as customers,
       avg((date_diff('day', s.first_ts, s.second_ts) <= w.n_days)::int)
           filter (where s.first_ts <= timestamp '2011-12-09' - to_days(w.n_days)) as repurchase_rate
from second s cross join w group by 1 order by 1;

-- output: uci_interpurchase_days
with g as (select date_diff('day', invoice_ts, lead(invoice_ts) over (partition by customer_id order by invoice_ts)) as gap
           from uci_inv)
select least(gap // 7, 26) * 7 as gap_week_start_days, count(*) as reorders
from g where gap is not null and gap > 0 group by 1 order by 1;

-- output: uci_summary
select count(distinct customer_id) as customers, count(*) as invoices, sum(amount_gbp) as revenue_gbp,
       count(*) / count(distinct customer_id) as invoices_per_customer,
       (select count(*) from (select customer_id from uci_inv group by 1 having count(*) >= 2)) / count(distinct customer_id) as repeat_customer_share,
       min(invoice_ts)::date as first_day, max(invoice_ts)::date as last_day
from uci_inv;
