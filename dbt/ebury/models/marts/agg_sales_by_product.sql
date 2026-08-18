-- Sales totals by product (clean fact only).
select
    f.product_id,
    p.product_name,
    count(*)            as num_transactions,
    sum(f.quantity)     as total_quantity,
    sum(f.subtotal)     as total_subtotal,
    sum(f.tax_amount)   as total_tax,
    sum(f.total_amount) as total_amount
from {{ ref('fct_transactions') }} f
join {{ ref('dim_product') }} p using (product_id)
group by 1, 2
order by f.product_id
