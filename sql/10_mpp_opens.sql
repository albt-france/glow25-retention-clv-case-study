-- 10_mpp_opens.sql  (SIMULATED)
-- From September 2025 machine opens (Apple Mail Privacy Protection) are recorded as opens.
-- Open rates jump; clicks do not. A subject-line test "won" on opens must be re-read on clicks and revenue.

-- output: email_monthly_engagement
select date_trunc('month', (sent_ts at time zone 'UTC') at time zone 'Europe/Berlin')::date as month,
       count(*) filter (where delivered) as delivered,
       count(*) filter (where opened) / count(*) filter (where delivered) as open_rate,
       count(*) filter (where opened and not mpp_flag) / count(*) filter (where delivered) as open_rate_excl_machine,
       count(*) filter (where mpp_flag) / nullif(count(*) filter (where opened), 0) as machine_share_of_opens,
       count(*) filter (where clicked) / count(*) filter (where delivered) as click_rate
from email_events where sent group by 1 order by 1;

-- output: subject_line_test_readout
-- "Autumn ritual (subject line test)", 14 Oct 2025, 50/50 split. Revenue = orders in the 5 days after the send (any source).
with r as (
    select e.variant, e.customer_id, e.opened, e.opened and not e.mpp_flag as human_open, e.clicked,
           coalesce((select sum(o.net_revenue_eur) from fct_order o where o.customer_id = e.customer_id
                     and o.ts_utc > e.sent_ts and o.ts_utc <= e.sent_ts + interval 5 day), 0) as revenue_5d
    from email_events e where e.flow_or_campaign like '%subject line test%' and e.delivered)
select variant, count(*) as delivered,
       avg(opened::int) as open_rate, avg(human_open::int) as open_rate_excl_machine,
       avg(clicked::int) as click_rate,
       1.96 * sqrt(avg(clicked::int) * (1 - avg(clicked::int)) / count(*)) as click_rate_ci95,
       avg(revenue_5d) as revenue_per_recipient_5d,
       1.96 * sqrt(var_samp(revenue_5d) / count(*)) as rpr_ci95
from r group by 1 order by 1;
