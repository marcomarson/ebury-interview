-- The case brief names a `fact_table`. Our canonical fact is fct_transactions; this thin
-- alias view fulfils the brief's literal name without duplicating logic.
{{ config(materialized='view') }}
select * from {{ ref('fct_transactions') }}
