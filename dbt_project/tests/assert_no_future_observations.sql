-- Forecast API may include near-future hours; fail only if observations are
-- unreasonably far ahead (more than 48h), which would indicate a parsing bug.
select
    city,
    observed_at
from {{ ref('stg_weather') }}
where observed_at > current_timestamp + interval '48 hours'
