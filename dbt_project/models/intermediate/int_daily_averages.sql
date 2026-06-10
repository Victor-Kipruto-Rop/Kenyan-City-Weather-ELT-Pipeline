select
    city,
    observation_date as day,
    round(avg(temperature_c)::numeric, 2) as avg_temp_c,
    round(sum(precipitation_mm)::numeric, 2) as total_precipitation_mm,
    round(avg(windspeed_kmh)::numeric, 2) as avg_windspeed_kmh,
    count(*) as hourly_readings
from {{ ref('stg_weather') }}
group by city, observation_date
