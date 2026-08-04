{{
    config(
        materialized='incremental',
        unique_key='vehicle_sk',
        incremental_strategy='delete+insert',
        on_schema_change='append_new_columns'
    )
}}

with enriched as (

    select * from {{ ref('int_vehicle_enriched') }}

    {% if is_incremental() %}
    where _extracted_at > (
        select coalesce(max(_extracted_at), '1900-01-01'::timestamp)
        from {{ this }}
    )
    {% endif %}

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['licence_plate']) }} as vehicle_sk,

        licence_plate,
        brand,
        trade_name,
        vehicle_type,
        body_type,
        powertrain_class,
        fuel_combination,

        first_admission_date,
        first_nl_registration_date,
        current_registration_date,
        nl_registration_year,
        date_trunc('month', first_nl_registration_date) as nl_registration_month,

        catalogue_price_eur,
        co2_combined_gkm,
        net_max_power_kw,
        electric_range_km,
        kerb_weight_kg,
        engine_displacement_cc,

        is_import,
        is_exported,
        apk_expired,
        apk_expiry_date,

        date_diff('year', first_nl_registration_date, current_date) as vehicle_age_years,

        _extracted_at

    from enriched
    where first_nl_registration_date is not null

)

select * from final