with vehicles as (

    select * from {{ ref('stg_vehicles') }}

),

fuel as (

    select * from {{ ref('int_fuel_by_vehicle') }}

),

body as (

    -- Body can fan out too (multiple carrosserie entries per plate).
    -- Take the lowest sequence number as the primary entry.
    select licence_plate, body_type, body_type_code
    from {{ ref('stg_body') }}
    qualify row_number() over (
        partition by licence_plate order by body_sequence
    ) = 1

),

enriched as (

    select
        v.licence_plate,
        v.vehicle_type,
        v.brand,
        v.trade_name,
        b.body_type,
        b.body_type_code,
        v.body_configuration,
        v.primary_colour,

        v.first_admission_date,
        v.first_nl_registration_date,
        v.current_registration_date,
        v.apk_expiry_date,

        year(v.first_nl_registration_date)  as nl_registration_year,
        year(v.first_admission_date)        as admission_year,

        v.catalogue_price_eur,
        v.kerb_weight_kg,
        v.seat_count,
        v.cylinder_count,
        v.engine_displacement_cc,

        coalesce(f.powertrain_class, 'Unknown')  as powertrain_class,
        f.fuel_combination,
        f.distinct_fuel_count,
        f.co2_combined_gkm,
        f.co2_weighted_gkm,
        f.net_max_power_kw,
        f.electric_range_km,
        f.euro_emission_standard,
        f.hybrid_class,

        -- Vehicles first admitted abroad and registered in NL materially
        -- later are parallel imports. 60 days absorbs normal
        -- administrative lag between admission and registration.
        case
            when v.first_admission_date is null
              or v.first_nl_registration_date is null then null
            when date_diff('day', v.first_admission_date,
                           v.first_nl_registration_date) > 60 then true
            else false
        end as is_import,

        v.apk_expiry_date < current_date  as apk_expired,
        v.export_indicator = 'Ja'         as is_exported,

        v._extracted_at

    from vehicles v
    left join fuel f using (licence_plate)
    left join body b using (licence_plate)

)

select * from enriched