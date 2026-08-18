-- Quarantine: rejected rows (broken measure) preserved verbatim + reasons. Never dropped.
select
    transaction_id_raw,
    customer_id_raw,
    transaction_date_raw,
    product_id_raw,
    product_name_raw,
    quantity_raw,
    price_raw,
    tax_raw,
    dq_reasons,
    _ingested_at,
    current_timestamp as _quarantined_at
from {{ ref('stg_customer_transactions') }}
where not is_valid
