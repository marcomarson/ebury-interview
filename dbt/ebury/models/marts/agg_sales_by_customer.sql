-- Sales totals by customer (clean fact only; -1 = unknown customer).
select
    customer_id,
    count(*)            as num_transactions,
    sum(quantity)       as total_quantity,
    sum(subtotal)       as total_subtotal,
    sum(tax_amount)     as total_tax,
    sum(total_amount)   as total_amount
from {{ ref('fct_transactions') }}
group by 1
order by customer_id
