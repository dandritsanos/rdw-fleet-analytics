with source as (

    select * from {{ source('rdw', 'body') }}

),

renamed as (

    select
        kenteken                                          as licence_plate,
        try_cast(carrosserie_volgnummer as integer)       as body_sequence,
        nullif(trim(type_carrosserie_europese_omschrijving), '') as body_type,
        nullif(trim(carrosserietype), '')                 as body_type_code,
        _extracted_at

    from source
    where kenteken is not null

)

select * from renamed