-- Product dimension. Natural key = product_id (already de-prefixed & consistent 1:1).
select distinct
    product_id,
    product_name
from {{ ref('int_transactions_valid') }}
order by product_id
