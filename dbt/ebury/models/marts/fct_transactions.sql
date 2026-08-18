-- Transaction fact (grain = one transaction). Built from clean rows only.
-- total_amount = quantity * unit_price + tax_amount (tax is an absolute amount, ADR 0005).
select
    transaction_id,
    customer_id,
    product_id,
    date_key,
    transaction_date,
    quantity,
    unit_price,
    subtotal,
    tax_amount,
    total_amount,
    missing_customer,
    _ingested_at
from {{ ref('int_transactions_valid') }}
