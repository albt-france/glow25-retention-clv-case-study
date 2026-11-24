-- 04_contribution_margin.sql  (SIMULATED)
-- Contribution margin per order = gross - discount - cost of goods - shipping - payment fees - refunds.
-- (Amounts are net of VAT; marketing and fixed costs are not in CM. Assumptions: docs/assumptions.md.)

create or replace table order_margin as
select o.*,
       case when o.is_subscription and s.interval = '3M' then 'subscription, every 3 months (-25%)'
            when o.is_subscription then 'subscription, monthly (-15%)'
            when o.campaign_code is not null then 'one-off, campaign'
            when o.order_seq = 1 then 'one-off, first order'
            else 'one-off, repeat' end as order_type
from fct_order o left join fct_subscription s using (subscription_id);

-- output: cm_by_order_type
select order_type, count(*) as orders,
       avg(gross_eur) as gross, avg(discount_eur) as discount, avg(cogs_eur) as cogs, avg(shipping_eur) as shipping,
       avg(payment_fee_eur) as payment_fee, avg(refund_eur) as refunds, avg(cm_eur) as cm_per_order,
       sum(cm_eur) / sum(gross_eur) as cm_share_of_gross,
       sum(cm_eur) as cm_total_eur
from order_margin group by rollup (order_type) order by orders desc;

-- output: cm_by_market
select market, count(*) as orders, avg(net_revenue_eur) as aov_net, avg(cm_eur) as cm_per_order,
       avg(shipping_eur) as shipping_per_order, sum(cm_eur) / sum(net_revenue_eur) as cm_rate
from order_margin group by market order by orders desc;

-- output: cm_waterfall
select 'gross' as step, sum(gross_eur) as eur from order_margin
union all select 'discounts', -sum(discount_eur) from order_margin
union all select 'cost of goods', -sum(cogs_eur) from order_margin
union all select 'shipping', -sum(shipping_eur) from order_margin
union all select 'payment fees', -sum(payment_fee_eur) from order_margin
union all select 'refunds', -sum(refund_eur) from order_margin
union all select 'contribution margin', sum(cm_eur) from order_margin;
