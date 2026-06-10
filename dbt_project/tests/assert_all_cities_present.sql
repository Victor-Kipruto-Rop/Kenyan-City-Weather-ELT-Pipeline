-- Each configured city must appear in staging at least once.
select city
from (
    values
        ('Nairobi'),
        ('Mombasa'),
        ('Eldoret')
) as expected(city)
where city not in (
    select distinct city from {{ ref('stg_weather') }}
)
