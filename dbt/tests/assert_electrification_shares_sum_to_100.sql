select
    registration_year,
    round(sum(share_of_year_pct), 2) as total_share_pct
from {{ ref('mart_fleet_electrification') }}
group by registration_year
having abs(sum(share_of_year_pct) - 100.0) > 0.02
