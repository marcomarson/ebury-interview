-- Clean transactions only (is_valid). Missing customer -> unknown member (-1).
select
    transaction_id,
    coalesce(customer_id, -1)                       as customer_id,
    product_id,
    product_name,
    transaction_date,
    to_char(transaction_date, 'YYYYMMDD')::int       as date_key,
    quantity,
    unit_price,
    subtotal,
    tax_amount,
    total_amount,
    missing_customer,
    _ingested_at
from {{ ref('stg_customer_transactions') }}
where is_valid
