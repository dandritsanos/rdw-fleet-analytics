with source as (

    select * from {{ source('rdw', 'fuel') }}

),

renamed as (

    select
        kenteken                                              as licence_plate,
        try_cast(brandstof_volgnummer as integer)             as fuel_sequence,
        nullif(
            upper(left(trim(brandstof_omschrijving), 1)) ||
            lower(substr(trim(brandstof_omschrijving), 2)),
            ''
        )                                                      as fuel_type,

        try_cast(co2_uitstoot_gecombineerd as integer)        as co2_combined_gkm,
        try_cast(co2_uitstoot_gewogen as integer)              as co2_weighted_gkm,
        try_cast(nettomaximumvermogen as decimal(10,2))       as net_max_power_kw,
        try_cast(actieradius as integer)                       as range_km,
        try_cast(actieradius_extern_oplaadbaar as integer)     as electric_range_km,
        try_cast(opgegeven_maximum_snelheid as decimal(10,2)) as declared_max_speed_kmh,

        nullif(trim(emissiecode_omschrijving), '')             as emission_code,
        nullif(trim(uitlaatemissieniveau), '')                 as euro_emission_standard,
        nullif(trim(klasse_hybride_elektrisch_voertuig), '')   as hybrid_class,

        _extracted_at

    from source
    where kenteken is not null
      and brandstof_omschrijving is not null

)

select * from renamed