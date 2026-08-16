-- Raw landing table for customer transactions.
-- Every source column is TEXT so the deliberately-dirty values (word-valued numbers,
-- mixed date formats, prefixed IDs, nulls) land verbatim and are NOT rejected at ingest.
-- Cleaning, casting, and validation happen downstream in dbt (plans 03-04).
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.customer_transactions (
    transaction_id   text,
    customer_id      text,
    transaction_date text,
    product_id       text,
    product_name     text,
    quantity         text,
    price            text,
    tax              text,
    -- ingestion metadata (lineage / audit)
    _ingested_at     timestamptz NOT NULL DEFAULT now(),
    _source_file     text
);
