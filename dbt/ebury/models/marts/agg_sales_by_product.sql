-- Sales summary by product (clean fact only), with insight metrics.
with product_sales as (
    select
        f.product_id,
        p.product_name,
        count(*)                     as num_transactions,
        sum(f.quantity)              as total_quantity,
        sum(f.subtotal)              as total_subtotal,
        sum(f.tax_amount)            as total_tax,
        sum(f.total_amount)          as total_amount,
        round(avg(f.unit_price), 2)  as avg_unit_price
    from {{ ref('fct_transactions') }} f
    join {{ ref('dim_product') }} p using (product_id)
    group by 1, 2
)
select
    *,
    round(100.0 * total_amount / sum(total_amount) over (), 1) as revenue_share_pct
from product_sales
order by product_id
