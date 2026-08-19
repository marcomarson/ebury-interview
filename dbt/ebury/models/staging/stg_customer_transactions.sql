-- Staging: coerce recoverable formatting and CLASSIFY each row (dq_reasons / is_valid).
-- No hard casts on dirty values — unparseable values become NULL and drive a dq reason,
-- so nothing errors and every raw row flows through (clean rows AND quarantine candidates).

with source as (
    select * from {{ source('raw', 'customer_transactions') }}
),

typed as (
    select
        -- original values preserved (for the quarantine audit trail)
        transaction_id   as transaction_id_raw,
        customer_id      as customer_id_raw,
        transaction_date as transaction_date_raw,
        product_id       as product_id_raw,
        product_name     as product_name_raw,
        quantity         as quantity_raw,
        price            as price_raw,
        tax              as tax_raw,

        -- coerced / typed values (NULL when unrecoverable)
        case when regexp_replace(coalesce(transaction_id, ''), '^T', '') ~ '^[0-9]+$'
             then regexp_replace(transaction_id, '^T', '')::bigint end            as transaction_id,
        case when regexp_replace(coalesce(customer_id, ''), '\.0+$', '') ~ '^[0-9]+$'
             then regexp_replace(customer_id, '\.0+$', '')::bigint end            as customer_id,
        case
            when transaction_date ~ '^\d{4}-\d{2}-\d{2}$' then to_date(transaction_date, 'YYYY-MM-DD')
            when transaction_date ~ '^\d{2}-\d{2}-\d{4}$' then to_date(transaction_date, 'DD-MM-YYYY')
        end                                                                        as transaction_date,
        case when regexp_replace(coalesce(product_id, ''), '^P', '') ~ '^[0-9]+$'
             then regexp_replace(product_id, '^P', '')::bigint end                as product_id,
        nullif(btrim(product_name), '')                                            as product_name,
        case when quantity ~ '^[0-9]+(\.[0-9]+)?$' then quantity::numeric::int end as quantity,
        case when price    ~ '^[0-9]+(\.[0-9]+)?$' then price::numeric end         as unit_price,
        case when tax      ~ '^[0-9]+(\.[0-9]+)?$' then tax::numeric end           as tax_amount,

        _ingested_at,
        _source_file
    from source
),

windowed as (
    select
        *,
        (transaction_id is not null
         and count(*) over (partition by transaction_id) > 1)                       as is_duplicate_id
    from typed
),

classified as (
    select
        *,
        -- Quarantine-first: any detectable issue segregates the row (with a reason) instead of
        -- failing the whole run — we decide later whether it's serious. The dbt tests downstream
        -- are the last-resort backstop, not the first line of defence.
        array_remove(array[
            -- unrecoverable measures (amount can't be computed)
            case when unit_price       is null then 'price_not_numeric' end,
            case when tax_amount       is null then 'tax_not_numeric' end,
            case when quantity         is null then 'quantity_missing_or_invalid' end,
            case when transaction_date is null then 'date_unparseable' end,
            case when transaction_id   is null then 'transaction_id_invalid' end,
            -- implausible values (numeric, but out of a valid range)
            case when unit_price is not null and unit_price <= 0 then 'price_non_positive' end,
            case when tax_amount is not null and tax_amount <  0 then 'tax_negative' end,
            case when quantity   is not null and quantity   <= 0 then 'quantity_non_positive' end,
            -- grain violation
            case when is_duplicate_id then 'duplicate_transaction_id' end
        ], null)                                                                   as dq_reasons,
        -- soft flag (kept): missing customer key
        (customer_id is null)                                                      as missing_customer
    from windowed
)

select
    *,
    (cardinality(dq_reasons) = 0)                                                  as is_valid,
    case when quantity is not null and unit_price is not null
         then (quantity * unit_price)::numeric end                                 as subtotal,
    case when quantity is not null and unit_price is not null and tax_amount is not null
         then (quantity * unit_price + tax_amount)::numeric end                    as total_amount
from classified
