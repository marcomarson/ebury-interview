-- Completeness metric: what share of received rows made it into the model vs quarantine.
{{ config(materialized='view') }}

with counts as (
    select
        (select count(*) from {{ source('raw', 'customer_transactions') }}) as rows_received,
        (select count(*) from {{ ref('fct_transactions') }})                as rows_modelled,
        (select count(*) from {{ ref('quarantine_customer_transactions') }}) as rows_quarantined
)
select
    rows_received,
    rows_modelled,
    rows_quarantined,
    (rows_modelled + rows_quarantined = rows_received)                       as reconciles,
    round(100.0 * rows_quarantined / nullif(rows_received, 0), 1)            as quarantine_pct
from counts
