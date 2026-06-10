select
    city,
    date_trunc('week', day)::date as week_start,
    round(avg(avg_temp_c)::numeric, 2) as weekly_avg_temp_c,
    round(sum(total_precipitation_mm)::numeric, 2) as weekly_precipitation_mm,
    round(avg(avg_windspeed_kmh)::numeric, 2) as weekly_avg_windspeed_kmh,
    sum(hourly_readings) as total_hourly_readings
from {{ ref('int_daily_averages') }}
group by city, date_trunc('week', day)::date
order by city, week_start
