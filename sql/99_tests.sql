-- 99_tests.sql  - assertions: the run stops with an error if one fails. Results in data/processed/tests.csv.

create or replace table test_results as
with t as (
    select 'no duplicate customer after staging (one canonical id per email_hash)' as test,
           (select count(*) from (select c.email_hash from dim_customer d join customers c using (customer_id)
                                  group by c.email_hash having count(*) > 1)) = 0 as passed
    union all
    select 'every order belongs to a canonical customer',
           (select count(*) from fct_order o left join dim_customer d using (customer_id) where d.customer_id is null) = 0
    union all
    select 'skipped charges are never counted as cancellations (a skipped subscription can stay active)',
           (select count(*) from fct_charge where is_skip and status <> 'skipped') = 0
           and (select count(*) from fct_subscription where skips > 0 and cancelled is null) > 0
    union all
    select 'contribution margin = gross - discount - COGS - shipping - fees - refunds (every order, 1 cent)',
           (select max(abs(cm_eur - (gross_eur - discount_eur - cogs_eur - shipping_eur - payment_fee_eur - refund_eur)))
            from fct_order) < 0.01
    union all
    select 'CM waterfall adds up',
           (select abs(sum(gross_eur) - sum(discount_eur) - sum(cogs_eur) - sum(shipping_eur) - sum(payment_fee_eur)
                       - sum(refund_eur) - sum(cm_eur)) from fct_order) < 1
    union all
    select 'holdout share of customers is 10 % +/- 0.5 pt in every flow with 2,000+ customers',
           (select bool_and(abs(holdout_share - 0.10) <= 0.005) from (
                select flow, avg(holdout::int) as holdout_share, count(*) as n
                from (select distinct flow, customer_id, holdout from flow_entries) group by flow) where n >= 2000)
    union all
    select 'Berlin time is never before UTC time',
           (select count(*) from fct_order where ts_berlin < ts_utc) = 0
    union all
    select 'order totals match the source table',
           abs((select sum(gross_eur) from fct_order) - (select sum(gross_eur) from orders)) < 0.01
)
select test, passed from t;

-- output: tests
select * from test_results;

select case when (select bool_and(passed) from test_results) then 'all tests passed'
            else error('a test in 99_tests.sql failed: see data/processed/tests.csv') end;
