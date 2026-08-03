with fuel as (

    select * from {{ ref('stg_fuel') }}

),

distinct_types as (

    select distinct licence_plate, fuel_type
    from fuel
    where fuel_type is not null

),

combination as (

    select
        licence_plate,
        string_agg(fuel_type, '+' order by fuel_type) as fuel_combination,
        count(*)                                       as distinct_fuel_count
    from distinct_types
    group by licence_plate

),

metrics as (

    select
        licence_plate,
        count(*)                        as fuel_row_count,
        max(co2_combined_gkm)           as co2_combined_gkm,
        max(co2_weighted_gkm)           as co2_weighted_gkm,
        max(net_max_power_kw)           as net_max_power_kw,
        max(electric_range_km)          as electric_range_km,
        max(range_km)                   as range_km,
        max(euro_emission_standard)     as euro_emission_standard,
        max(hybrid_class)               as hybrid_class,
        bool_or(fuel_type = 'Elektriciteit')                                   as has_electric,
        bool_or(fuel_type = 'Waterstof')                                       as has_hydrogen,
        bool_or(fuel_type in ('Benzine','Diesel','Lpg','Cng','Alcohol'))       as has_combustion
    from fuel
    group by licence_plate

),

classified as (

    select
        m.licence_plate,
        c.fuel_combination,
        c.distinct_fuel_count,
        m.fuel_row_count,
        m.co2_combined_gkm,
        m.co2_weighted_gkm,
        m.net_max_power_kw,
        m.electric_range_km,
        m.range_km,
        m.euro_emission_standard,
        m.hybrid_class,
        m.has_electric,
        m.has_combustion,

        -- Order matters: hydrogen first, or an FCEV with neither the
        -- electric nor combustion flag set falls through to 'ICE'.
        case
            when m.has_hydrogen                          then 'FCEV'
            when m.has_electric and not m.has_combustion  then 'BEV'
            when m.has_electric and m.has_combustion      then 'Hybrid / PHEV'
            when m.has_combustion                         then 'ICE'
            else 'Unknown'
        end as powertrain_class

    from metrics m
    left join combination c using (licence_plate)

)

select * from classified