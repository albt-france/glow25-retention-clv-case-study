-- 05_flow_holdout_readout.sql  (SIMULATED)
-- Attributed revenue (last touch: click within 5 days, else open within 1 day) vs incremental revenue
-- (treated minus a permanent 10 % holdout, per recipient, over a fixed window after the flow trigger).
-- Incremental revenue = (revenue per treated recipient - revenue per holdout recipient) x treated recipients.

create or replace table flow_window as
select * from (values
    ('F1_welcome', 14), ('F2_education', 45), ('F3_trial_to_sub', 30), ('F4_replenishment', 60),
    ('F5_sub_onboarding', 90), ('F6_cancel_save', 60), ('F7_winback', 30), ('F8_vip_loyalty', 30),
    ('VIP early access (Gold)', 7)) t(flow, window_days);

create or replace macro flow_name(x) as case when x like '%early access (Gold)%' then 'VIP early access (Gold)' else x end;

create or replace table flow_entries as
select flow_name(e.flow_or_campaign) as flow, e.customer_id, e.entry_ts,
       bool_or(e.holdout_flag) as holdout, any_value(e.variant) as variant,
       min(e.send_id) as first_send_id
from email_events e join flow_window w on w.flow = flow_name(e.flow_or_campaign)
group by all;

create or replace table flow_outcome as
select fe.flow, fe.customer_id, fe.entry_ts, fe.holdout, fe.variant, w.window_days,
       coalesce(sum(o.net_revenue_eur), 0) as revenue_eur,
       coalesce(sum(o.cm_eur), 0) as cm_eur,
       count(o.order_id) > 0 as converted
from flow_entries fe
join flow_window w using (flow)
left join fct_order o
       on o.customer_id = fe.customer_id
      and o.ts_utc > fe.entry_ts
      and o.ts_utc <= fe.entry_ts + to_days(w.window_days)
where fe.entry_ts + to_days(w.window_days) <= timestamp '2026-10-31 23:59:59'
group by all;

-- attributed revenue of the sends that belong to the same (complete-window) entries
create or replace table flow_attributed as
select flow_name(e.flow_or_campaign) as flow, sum(a.attributed_revenue_eur) as attributed_eur
from attributed_orders a
join email_events e using (send_id)
join flow_window w on w.flow = flow_name(e.flow_or_campaign)
where e.entry_ts + to_days(w.window_days) <= timestamp '2026-10-31 23:59:59'
group by 1;

-- output: flow_holdout_readout
with arms as (
    select flow,
           count(*) filter (where not holdout) as n_t, count(*) filter (where holdout) as n_h,
           avg(revenue_eur) filter (where not holdout) as rpr_t, avg(revenue_eur) filter (where holdout) as rpr_h,
           var_samp(revenue_eur) filter (where not holdout) as var_t, var_samp(revenue_eur) filter (where holdout) as var_h,
           avg(cm_eur) filter (where not holdout) as cmpr_t, avg(cm_eur) filter (where holdout) as cmpr_h,
           var_samp(cm_eur) filter (where not holdout) as cvar_t, var_samp(cm_eur) filter (where holdout) as cvar_h,
           avg(converted::int) filter (where not holdout) as conv_t, avg(converted::int) filter (where holdout) as conv_h
    from flow_outcome group by flow),
whole as (select flow_name(flow_or_campaign) as flow, sum(attributed_revenue_eur) as attributed_eur_all_period
          from attributed_orders group by 1)
select a.flow, w.window_days, a.n_t, a.n_h, a.n_h / (a.n_t + a.n_h) as holdout_share,
       a.conv_t, a.conv_h, a.rpr_t, a.rpr_h,
       a.rpr_t - a.rpr_h as rpr_diff,
       1.96 * sqrt(a.var_t / a.n_t + a.var_h / a.n_h) as rpr_diff_ci95,
       (a.rpr_t - a.rpr_h) * a.n_t as incremental_revenue_eur,
       1.96 * sqrt(a.var_t / a.n_t + a.var_h / a.n_h) * a.n_t as incremental_revenue_ci95,
       (a.cmpr_t - a.cmpr_h) * a.n_t as incremental_cm_eur,
       1.96 * sqrt(a.cvar_t / a.n_t + a.cvar_h / a.n_h) * a.n_t as incremental_cm_ci95,
       fa.attributed_eur as attributed_revenue_eur,
       (a.rpr_t - a.rpr_h) * a.n_t / nullif(fa.attributed_eur, 0) as incremental_share_of_attributed,
       1.96 * sqrt(a.var_t / a.n_t + a.var_h / a.n_h) * a.n_t / nullif(fa.attributed_eur, 0) as incremental_share_ci95,
       wh.attributed_eur_all_period
from arms a join flow_window w using (flow)
left join flow_attributed fa using (flow)
left join whole wh using (flow)
order by attributed_eur_all_period desc nulls last;

-- output: localisation_fr_welcome_test
-- FR only, Mar 2025 - Feb 2026: welcome translated from the German flow vs welcome rewritten for France (beauty, ritual)
select fe.variant, count(*) as recipients,
       avg(fo.revenue_eur) as revenue_per_recipient_14d,
       1.96 * sqrt(var_samp(fo.revenue_eur) / count(*)) as rpr_ci95,
       avg(fo.converted::int) as purchase_rate_14d,
       (select count(*) filter (where unsubscribed) / count(*) filter (where delivered) from email_events e
         where e.flow_or_campaign = 'F1_welcome' and e.variant = fe.variant) as unsubscribe_rate_per_email
from flow_entries fe join flow_outcome fo using (flow, customer_id, entry_ts)
where fe.flow = 'F1_welcome' and fe.variant in ('FR_translated', 'FR_adapted') and not fe.holdout
group by fe.variant order by fe.variant;
