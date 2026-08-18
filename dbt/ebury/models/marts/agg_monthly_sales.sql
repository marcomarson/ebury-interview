-- Monthly sales summary (clean fact only), with insight metrics.
select
    date_trunc('month', transaction_date)::date                  as month,
    count(*)                                                      as num_transactions,
    count(distinct customer_id) filter (where customer_id <> -1)  as num_customers,
    count(distinct product_id)                                   as distinct_products,
    sum(quantity)                                                as total_quantity,
    sum(subtotal)                                                as total_subtotal,
    sum(tax_amount)                                              as total_tax,
    sum(total_amount)                                            as total_amount,
    round(avg(total_amount), 2)                                  as avg_transaction_value,
    round(sum(quantity)::numeric / nullif(count(*), 0), 2)       as avg_units_per_transaction
from {{ ref('fct_transactions') }}
group by 1
order by 1
