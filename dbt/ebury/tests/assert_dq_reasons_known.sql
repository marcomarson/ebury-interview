-- The dq reason vocabulary is controlled: every reason must be a known code.
with known as (
    select unnest(array[
        'price_not_numeric',
        'tax_not_numeric',
        'quantity_missing_or_invalid',
        'date_unparseable',
        'transaction_id_invalid',
        'price_non_positive',
        'tax_negative',
        'quantity_non_positive',
        'duplicate_transaction_id'
    ]) as reason
)
select r.transaction_id_raw, r.dq_reason
from {{ ref('dq_quarantine_reasons') }} r
where r.dq_reason not in (select reason from known)
