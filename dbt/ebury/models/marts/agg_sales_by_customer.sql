-- Sales summary by customer (clean fact only; -1 = unknown customer), with insight metrics.
select
    customer_id,
    (customer_id = -1)          as is_unknown,
    count(*)                    as num_transactions,
    count(distinct product_id)  as distinct_products,
    sum(quantity)               as total_quantity,
    sum(subtotal)               as total_subtotal,
    sum(tax_amount)             as total_tax,
    sum(total_amount)           as total_amount,
    round(avg(total_amount), 2) as avg_transaction_value,
    min(transaction_date)       as first_transaction_date,
    max(transaction_date)       as last_transaction_date
from {{ ref('fct_transactions') }}
group by 1
order by customer_id
