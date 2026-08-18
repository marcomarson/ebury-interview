-- Deeper analysis of `tax` (plan 03): is it an absolute amount or a rate (%)?
-- Discriminators: correlation with price/subtotal (a rate correlates; an absolute
-- amount does not) and whether tax/price clusters at a few round percentages.

\echo '=== A. tax summary (numeric rows) ==='
SELECT count(*) AS n, round(min(tax::numeric),2) AS min, round(max(tax::numeric),2) AS max,
       round(avg(tax::numeric),2) AS avg, round(stddev(tax::numeric),2) AS stddev,
       count(*) FILTER (WHERE tax::numeric = round(tax::numeric)) AS whole_numbers
FROM raw.customer_transactions WHERE tax ~ '^[0-9]+(\.[0-9]+)?$';

\echo '=== B. correlation: tax vs price, and tax vs (qty*price) ==='
SELECT round(corr(tax::numeric, price::numeric)::numeric,3) AS corr_tax_price
FROM raw.customer_transactions
WHERE tax ~ '^[0-9]+(\.[0-9]+)?$' AND price ~ '^[0-9]+(\.[0-9]+)?$';
SELECT round(corr(tax::numeric, quantity::numeric*price::numeric)::numeric,3) AS corr_tax_subtotal
FROM raw.customer_transactions
WHERE tax ~ '^[0-9]+(\.[0-9]+)?$' AND price ~ '^[0-9]+(\.[0-9]+)?$' AND quantity ~ '^[0-9]+(\.[0-9]+)?$';

\echo '=== C. tax as % of UNIT PRICE (bucketed to nearest 5%) ==='
SELECT (round((tax::numeric/price::numeric*100)/5)*5)::int AS pct_of_price_bucket, count(*) AS n
FROM raw.customer_transactions
WHERE tax ~ '^[0-9]+(\.[0-9]+)?$' AND price ~ '^[0-9]+(\.[0-9]+)?$'
GROUP BY 1 ORDER BY 1;

\echo '=== D. tax as % of LINE SUBTOTAL qty*price (bucketed to nearest 5%) ==='
SELECT (round((tax::numeric/(quantity::numeric*price::numeric)*100)/5)*5)::int AS pct_of_subtotal_bucket, count(*) AS n
FROM raw.customer_transactions
WHERE tax ~ '^[0-9]+(\.[0-9]+)?$' AND price ~ '^[0-9]+(\.[0-9]+)?$' AND quantity ~ '^[0-9]+(\.[0-9]+)?$'
GROUP BY 1 ORDER BY 1;
