{% snapshot snap_vehicle_state %}

{{
    config(
        unique_key='licence_plate',
        strategy='check',
        check_cols=[
            'current_registration_date',
            'apk_expiry_date',
            'insured_indicator',
            'export_indicator'
        ],
        hard_deletes='invalidate'
    )
}}

select
    kenteken                                        as licence_plate,
    {{ rdw_date('datum_tenaamstelling') }}          as current_registration_date,
    {{ rdw_date('vervaldatum_apk') }}               as apk_expiry_date,
    nullif(upper(trim(wam_verzekerd)), '')          as insured_indicator,
    nullif(upper(trim(export_indicator)), '')       as export_indicator,
    nullif(upper(trim(merk)), '')                   as brand
from {{ source('rdw', 'vehicles') }}
where kenteken is not null

{% endsnapshot %}