with source as (

    select * from {{ source('rdw', 'vehicles') }}

),

renamed as (

    select
        kenteken as licence_plate,
        nullif(trim(voertuigsoort), '') as vehicle_type,
        nullif(upper(trim(merk)), '') as brand,
        nullif(trim(handelsbenaming), '') as trade_name,
        nullif(lower(trim(inrichting)), '') as body_configuration,
        nullif(upper(trim(eerste_kleur)), '') as primary_colour,

        {{ rdw_date('datum_eerste_toelating') }} as first_admission_date,
        {{ rdw_date('datum_eerste_tenaamstelling_in_nederland') }} as first_nl_registration_date,
        {{ rdw_date('datum_tenaamstelling') }} as current_registration_date,
        {{ rdw_date('vervaldatum_apk') }} as apk_expiry_date,

        try_cast(catalogusprijs as decimal(12,2)) as catalogue_price_eur,
        try_cast(massa_ledig_voertuig as integer) as kerb_weight_kg,
        try_cast(aantal_zitplaatsen as integer) as seat_count,
        try_cast(aantal_cilinders as integer) as cylinder_count,
        try_cast(cilinderinhoud as integer) as engine_displacement_cc,

        nullif(upper(trim(export_indicator)), '') as export_indicator,
        nullif(upper(trim(wam_verzekerd)), '') as insured_indicator,

        _extracted_at

    from source
    where kenteken is not null

)

select * from renamed