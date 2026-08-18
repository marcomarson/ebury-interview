-- Date dimension via a spine (covers the whole month, not just observed dates).
with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2023-07-01' as date)",
        end_date="cast('2023-08-01' as date)"
    ) }}
)
select
    to_char(date_day, 'YYYYMMDD')::int      as date_key,
    date_day::date                          as date_day,
    extract(year  from date_day)::int       as year,
    extract(month from date_day)::int       as month,
    extract(day   from date_day)::int       as day,
    to_char(date_day, 'Mon')                as month_name,
    extract(isodow from date_day)::int      as day_of_week
from spine
