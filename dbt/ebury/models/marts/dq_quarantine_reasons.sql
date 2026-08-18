-- Unnest the quarantine reasons so issues can be counted per reason.
{{ config(materialized='view') }}

select
    transaction_id_raw,
    unnest(dq_reasons) as dq_reason,
    _quarantined_at
from {{ ref('quarantine_customer_transactions') }}
