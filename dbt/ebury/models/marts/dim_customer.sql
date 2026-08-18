-- Customer dimension. Thin (only customer_id in the source) + an explicit unknown member
-- (-1) so fact rows with a missing customer keep referential integrity.
with customers as (
    select distinct customer_id
    from {{ ref('int_transactions_valid') }}
    where customer_id <> -1
)
select
    customer_id,
    false as is_unknown
from customers

union all

select
    -1          as customer_id,
    true        as is_unknown
