-- The case brief names a `dim_table`. Our canonical dimension is dim_product; this thin
-- alias view fulfils the brief's literal name without duplicating logic.
{{ config(materialized='view') }}
select * from {{ ref('dim_product') }}
