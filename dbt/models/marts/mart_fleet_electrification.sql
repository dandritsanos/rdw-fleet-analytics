with base as (

    select * from {{ ref('fct_vehicle_registration') }}
    where nl_registration_year between 2010 and year(current_date)

),

by_year as (

    select
        nl_registration_year                       as registration_year,
        powertrain_class,
        count(*)                                   as vehicles,
        round(avg(co2_combined_gkm), 1)            as avg_co2_gkm,
        round(median(catalogue_price_eur), 0)      as median_catalogue_price_eur,
        round(avg(electric_range_km), 0)           as avg_electric_range_km,
        round(avg(net_max_power_kw), 1)            as avg_power_kw
    from base
    group by 1, 2

),

with_share as (

    select
        *,
        sum(vehicles) over (partition by registration_year)  as year_total_vehicles,
        round(
            100.0 * vehicles
                  / sum(vehicles) over (partition by registration_year)
        , 2) as share_of_year_pct
    from by_year

),

with_change as (

    select
        *,
        round(
            share_of_year_pct
          - lag(share_of_year_pct) over (
                partition by powertrain_class order by registration_year
            )
        , 2) as share_change_pp
    from with_share

)

select * from with_change
order by registration_year, powertrain_class