-- total_amount must equal quantity * unit_price + tax_amount (ADR 0005).
select
    transaction_id,
    total_amount,
    quantity,
    unit_price,
    tax_amount
from {{ ref('fct_transactions') }}
where total_amount <> (quantity * unit_price + tax_amount)
