-- Quarantine observability: WARN whenever any row is quarantined; ERROR only in the
-- extreme (>= 50 rows here — configurable). Quarantining is expected, not a failure.
{{ config(severity='warn', warn_if='>0', error_if='>=50') }}

select
    transaction_id_raw,
    dq_reasons
from {{ ref('quarantine_customer_transactions') }}
