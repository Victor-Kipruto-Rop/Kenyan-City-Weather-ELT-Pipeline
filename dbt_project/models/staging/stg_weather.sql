with source as (
    select *
    from {{ source('weather_raw', 'raw_weather') }}
),

cleaned as (
    select
        city,
        timestamp::timestamptz as observed_at,
        temperature::double precision as temperature_c,
        precipitation::double precision as precipitation_mm,
        windspeed::double precision as windspeed_kmh,
        ingested_at::timestamptz as ingested_at,
        date(timestamp::timestamptz) as observation_date
    from source
    where city is not null
      and timestamp is not null
)

select * from cleaned
