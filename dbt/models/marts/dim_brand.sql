with vehicles as (

    select * from {{ ref('int_vehicle_enriched') }}
    where brand is not null

),

agg as (

    select
        brand,
        count(*)                                          as total_vehicles,
        count(distinct trade_name)                         as distinct_models,
        min(first_nl_registration_date)                    as first_seen_in_nl,
        max(first_nl_registration_date)                    as last_seen_in_nl,
        round(avg(catalogue_price_eur), 0)                 as avg_catalogue_price_eur,
        round(median(catalogue_price_eur), 0)              as median_catalogue_price_eur,
        round(avg(co2_combined_gkm), 1)                    as avg_co2_gkm,
        sum(case when powertrain_class = 'BEV' then 1 else 0 end)  as bev_count,
        sum(case when is_import then 1 else 0 end)                  as import_count
    from vehicles
    group by brand

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['brand']) }} as brand_sk,
        brand,
        total_vehicles,
        distinct_models,
        first_seen_in_nl,
        last_seen_in_nl,
        avg_catalogue_price_eur,
        median_catalogue_price_eur,
        avg_co2_gkm,
        bev_count,
        
        round(100.0 * bev_count / nullif(total_vehicles, 0), 2)   as bev_share_pct,
        round(100.0 * import_count / nullif(total_vehicles, 0), 2) as import_share_pct,

        case
            when total_vehicles >= 10000 then 'volume'
            when total_vehicles >= 1000  then 'mainstream'
            when total_vehicles >= 50    then 'niche'
            else 'marginal'
        end as brand_tier

    from agg

)

select * from final
order by total_vehicles desc