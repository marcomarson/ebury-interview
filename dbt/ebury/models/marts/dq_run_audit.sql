-- DQ history: one row appended per dbt run (invocation), so quarantine trends are
-- observable over time (not just the current snapshot in dq_completeness).
{{ config(materialized='incremental', unique_key='invocation_id') }}

with reasons as (
    select dq_reason, count(*) as n
    from {{ ref('dq_quarantine_reasons') }}
    group by 1
),
current_run as (
    select
        '{{ invocation_id }}'::text                                            as invocation_id,
        '{{ run_started_at }}'::timestamptz                                    as run_started_at,
        c.rows_received,
        c.rows_modelled,
        c.rows_quarantined,
        c.quarantine_pct,
        coalesce((select n from reasons where dq_reason = 'price_not_numeric'), 0)           as n_price_not_numeric,
        coalesce((select n from reasons where dq_reason = 'tax_not_numeric'), 0)             as n_tax_not_numeric,
        coalesce((select n from reasons where dq_reason = 'quantity_missing_or_invalid'), 0) as n_quantity_invalid,
        coalesce((select n from reasons where dq_reason = 'date_unparseable'), 0)            as n_date_unparseable,
        coalesce((select n from reasons where dq_reason = 'transaction_id_invalid'), 0)      as n_transaction_id_invalid
    from {{ ref('dq_completeness') }} c
)
select * from current_run
{% if is_incremental() %}
where invocation_id not in (select invocation_id from {{ this }})
{% endif %}
