-- Monthly sales totals (clean fact only).
select
    date_trunc('month', transaction_date)::date                 as month,
    count(*)                                                     as num_transactions,
    count(distinct customer_id) filter (where customer_id <> -1) as num_customers,
    sum(quantity)                                               as total_quantity,
    sum(subtotal)                                              as total_subtotal,
    sum(tax_amount)                                            as total_tax,
    sum(total_amount)                                          as total_amount
from {{ ref('fct_transactions') }}
group by 1
order by 1
