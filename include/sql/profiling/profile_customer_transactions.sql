-- Profiling of raw.customer_transactions (plan 03).
-- Read-only: quantifies each data-quality issue to ground the coerce/quarantine/flag rules.
-- Casts are guarded with CASE so non-numeric values never raise errors.

\echo '=== 1. total rows ==='
SELECT count(*) AS total_rows FROM raw.customer_transactions;

\echo '=== 2. completeness: missing (NULL or empty) per column ==='
SELECT
  count(*) FILTER (WHERE transaction_id   IS NULL OR btrim(transaction_id)='')   AS tx_id_missing,
  count(*) FILTER (WHERE customer_id       IS NULL OR btrim(customer_id)='')       AS customer_id_missing,
  count(*) FILTER (WHERE transaction_date  IS NULL OR btrim(transaction_date)='')  AS date_missing,
  count(*) FILTER (WHERE product_id        IS NULL OR btrim(product_id)='')        AS product_id_missing,
  count(*) FILTER (WHERE product_name      IS NULL OR btrim(product_name)='')      AS product_name_missing,
  count(*) FILTER (WHERE quantity          IS NULL OR btrim(quantity)='')          AS quantity_missing,
  count(*) FILTER (WHERE price             IS NULL OR btrim(price)='')             AS price_missing,
  count(*) FILTER (WHERE tax               IS NULL OR btrim(tax)='')               AS tax_missing
FROM raw.customer_transactions;

\echo '=== 3. transaction_id: prefix, numeric-after-strip, uniqueness ==='
SELECT
  count(*) FILTER (WHERE transaction_id LIKE 'T%')                                  AS t_prefixed,
  count(*) FILTER (WHERE regexp_replace(transaction_id,'^T','') ~ '^[0-9]+$')       AS numeric_after_strip,
  count(DISTINCT regexp_replace(transaction_id,'^T',''))                            AS distinct_after_strip,
  count(*)                                                                          AS total
FROM raw.customer_transactions;

\echo '=== 3b. transaction_id duplicates after stripping T ==='
SELECT regexp_replace(transaction_id,'^T','') AS tx_id, count(*) AS n
FROM raw.customer_transactions GROUP BY 1 HAVING count(*) > 1 ORDER BY 2 DESC;

\echo '=== 4. customer_id: float form vs int vs missing ==='
SELECT
  count(*) FILTER (WHERE customer_id ~ '^[0-9]+\.0+$')                 AS float_form,
  count(*) FILTER (WHERE customer_id ~ '^[0-9]+$')                     AS int_form,
  count(*) FILTER (WHERE customer_id IS NULL OR btrim(customer_id)='') AS missing,
  count(DISTINCT customer_id)                                         AS distinct_vals
FROM raw.customer_transactions;

\echo '=== 5. transaction_date: format split ==='
SELECT
  count(*) FILTER (WHERE transaction_date ~ '^\d{4}-\d{2}-\d{2}$') AS iso_ymd,
  count(*) FILTER (WHERE transaction_date ~ '^\d{2}-\d{2}-\d{4}$') AS dmy,
  count(*) FILTER (WHERE transaction_date !~ '^\d{4}-\d{2}-\d{2}$'
                    AND transaction_date !~ '^\d{2}-\d{2}-\d{4}$')  AS other
FROM raw.customer_transactions;

\echo '=== 5b. parsed date range (both formats) ==='
SELECT min(d) AS min_date, max(d) AS max_date FROM (
  SELECT CASE
    WHEN transaction_date ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(transaction_date,'YYYY-MM-DD')
    WHEN transaction_date ~ '^\d{2}-\d{2}-\d{4}$' THEN to_date(transaction_date,'DD-MM-YYYY')
  END AS d FROM raw.customer_transactions
) s;

\echo '=== 6. product_id: prefix + distinct after strip ==='
SELECT
  count(*) FILTER (WHERE product_id LIKE 'P%')                    AS p_prefixed,
  count(DISTINCT regexp_replace(product_id,'^P',''))             AS distinct_after_strip
FROM raw.customer_transactions;

\echo '=== 6b. normalized product_id -> product_name mapping (should be 1:1) ==='
SELECT regexp_replace(product_id,'^P','') AS pid, product_name, count(*) AS n
FROM raw.customer_transactions GROUP BY 1,2 ORDER BY 1;

\echo '=== 7. quantity: missing / numeric / integer / zero-or-negative ==='
SELECT
  count(*) FILTER (WHERE quantity IS NULL OR btrim(quantity)='')           AS missing,
  count(*) FILTER (WHERE quantity ~ '^[0-9]+(\.[0-9]+)?$')                 AS numeric_vals,
  count(*) FILTER (WHERE quantity ~ '^[0-9]+$')                            AS integer_vals,
  count(*) FILTER (WHERE CASE WHEN quantity ~ '^[0-9]+(\.[0-9]+)?$'
                              THEN quantity::numeric <= 0 ELSE false END)  AS zero_or_negative
FROM raw.customer_transactions;

\echo '=== 8. price: numeric vs non-numeric (word values) ==='
SELECT
  count(*) FILTER (WHERE price ~ '^[0-9]+(\.[0-9]+)?$')  AS numeric_vals,
  count(*) FILTER (WHERE price !~ '^[0-9]+(\.[0-9]+)?$') AS non_numeric_vals
FROM raw.customer_transactions;

\echo '=== 8b. distinct non-numeric price values ==='
SELECT price AS bad_price_value, count(*) AS n
FROM raw.customer_transactions
WHERE price !~ '^[0-9]+(\.[0-9]+)?$' GROUP BY 1 ORDER BY 2 DESC;

\echo '=== 9. tax: numeric vs non-numeric ==='
SELECT
  count(*) FILTER (WHERE tax ~ '^[0-9]+(\.[0-9]+)?$')  AS numeric_vals,
  count(*) FILTER (WHERE tax !~ '^[0-9]+(\.[0-9]+)?$') AS non_numeric_vals
FROM raw.customer_transactions;

\echo '=== 9b. distinct non-numeric tax values ==='
SELECT tax AS bad_tax_value, count(*) AS n
FROM raw.customer_transactions
WHERE tax !~ '^[0-9]+(\.[0-9]+)?$' GROUP BY 1 ORDER BY 2 DESC;

\echo '=== 10. tax vs price: absolute amount or a rate? (numeric rows only) ==='
SELECT
  round(min(tax::numeric),2)   AS min_tax,
  round(max(tax::numeric),2)   AS max_tax,
  round(avg(tax::numeric),2)   AS avg_tax,
  round(min(price::numeric),2) AS min_price,
  round(max(price::numeric),2) AS max_price,
  round(avg(tax::numeric / nullif(price::numeric,0))*100,1) AS avg_tax_pct_of_price
FROM raw.customer_transactions
WHERE tax ~ '^[0-9]+(\.[0-9]+)?$' AND price ~ '^[0-9]+(\.[0-9]+)?$';

\echo '=== 11. quarantine vs flag vs clean preview ==='
WITH classified AS (
  SELECT
    (price    !~ '^[0-9]+(\.[0-9]+)?$')                                       AS bad_price,
    (tax      !~ '^[0-9]+(\.[0-9]+)?$')                                       AS bad_tax,
    (quantity IS NULL OR btrim(quantity)='' OR quantity !~ '^[0-9]+(\.[0-9]+)?$') AS bad_qty,
    (customer_id IS NULL OR btrim(customer_id)='')                            AS missing_customer
  FROM raw.customer_transactions
)
SELECT
  count(*) FILTER (WHERE bad_price OR bad_tax OR bad_qty)                                  AS would_quarantine,
  count(*) FILTER (WHERE NOT (bad_price OR bad_tax OR bad_qty) AND missing_customer)        AS clean_but_flagged,
  count(*) FILTER (WHERE NOT (bad_price OR bad_tax OR bad_qty) AND NOT missing_customer)    AS fully_clean,
  count(*)                                                                                  AS total
FROM classified;

\echo '=== 11b. issue overlap (how many issues per row) ==='
WITH classified AS (
  SELECT
    (price    !~ '^[0-9]+(\.[0-9]+)?$')::int                                       AS bad_price,
    (tax      !~ '^[0-9]+(\.[0-9]+)?$')::int                                       AS bad_tax,
    (quantity IS NULL OR btrim(quantity)='' OR quantity !~ '^[0-9]+(\.[0-9]+)?$')::int AS bad_qty,
    (customer_id IS NULL OR btrim(customer_id)='')::int                            AS missing_customer
  FROM raw.customer_transactions
)
SELECT (bad_price+bad_tax+bad_qty+missing_customer) AS issues_on_row, count(*) AS n_rows
FROM classified GROUP BY 1 ORDER BY 1;
