# Data Dictionary — RDW Fleet Analytics

**Source:** RDW Open Data (Socrata), `opendata.rdw.nl`
**Extract:** `scripts/extract_rdw.py`
**Scope:** Passenger cars (`voertuigsoort = 'Personenauto'`), admission year 2010+
**Status:** In development
**Last extract:** 2026-07-31

---

## Extract summary

| Metric | Value |
|---|---|
| Vehicles | 300,000 |
| Fuel rows | 359,438 |
| Body rows | 296,007 |
| Extract duration | 8m 17s |
| Fuel fan-out | 19.8% of vehicles have 2+ fuel rows (multi-fuel/hybrid vehicles) |
| Body coverage gap | 1.3% of vehicles have no body record |
| Pagination integrity | Vehicle row count == distinct plate count at 300K scale (verified) |

---

## Model layer overview

| Layer | Model | Grain | Materialization |
|---|---|---|---|
| Staging | `stg_vehicles`, `stg_fuel`, `stg_body` | One row per source record | view |
| Intermediate | `int_fuel_by_vehicle` | One row per licence_plate | table |
| Intermediate | `int_vehicle_enriched` | One row per licence_plate | table |
| Marts | `dim_brand` | One row per brand | table |
| Marts | `fct_vehicle_registration` | One row per licence_plate | incremental table |
| Marts | `mart_fleet_electrification` | One row per (registration_year, powertrain_class) | table |
| Snapshot | `snap_vehicle_state` | One row per licence_plate per tracked version | snapshot (SCD Type 2) |

---

## raw.vehicles

64 columns as delivered by the API. Selected subset used downstream:

| Raw column | Staging column | Type (staged) | Notes |
|---|---|---|---|
| `kenteken` | `licence_plate` | varchar | Primary key, not null enforced |
| `voertuigsoort` | `vehicle_type` | varchar | Filtered to `Personenauto` at extract time |
| `merk` | `brand` | varchar | Upper-cased |
| `handelsbenaming` | `trade_name` | varchar | |
| `inrichting` | `body_configuration` | varchar | Lower-cased |
| `eerste_kleur` | `primary_colour` | varchar | Upper-cased |
| `datum_eerste_toelating` | `first_admission_date` | date | YYYYMMDD string, parsed via `rdw_date` macro |
| `datum_eerste_tenaamstelling_in_nederland` | `first_nl_registration_date` | date | Used for `is_import` derivation |
| `datum_tenaamstelling` | `current_registration_date` | date | Tracked over time in `snap_vehicle_state` |
| `vervaldatum_apk` | `apk_expiry_date` | date | Tracked over time in `snap_vehicle_state` |
| `catalogusprijs` | `catalogue_price_eur` | decimal(12,2) | Absent on trailers/commercial vehicles |
| `massa_ledig_voertuig` | `kerb_weight_kg` | integer | |
| `aantal_zitplaatsen` | `seat_count` | integer | |
| `aantal_cilinders` | `cylinder_count` | integer | |
| `cilinderinhoud` | `engine_displacement_cc` | integer | |
| `export_indicator` | `export_indicator` | varchar | Raw Ja/Nee, not boolean. Tracked over time in `snap_vehicle_state` |
| `wam_verzekerd` | `insured_indicator` | varchar | Three states: Ja/Nee/N.v.t. — not boolean, see note. Tracked over time in `snap_vehicle_state` |

**`wam_verzekerd` is not boolean.** The register includes a third state (`N.v.t.`) for vehicle types where insurance status doesn't apply (e.g. trailers). Modelled as a raw string, not cast to boolean.

**`datum_*_dt` columns exist and are unused by design.** RDW provides pre-parsed ISO timestamp twins of every date field (e.g. `datum_tenaamstelling_dt`). Not used; dates are parsed from the raw `YYYYMMDD` string via the `rdw_date` macro instead, keeping parsing logic and failure handling under our control rather than dependent on the source's own conversion.

**`api_gekentekende_voertuigen_*` columns** are self-referential URLs to related Socrata datasets (assen, brandstof, carrosserie, etc.), not data fields. Not selected in staging.

---

## raw.fuel

**Grain: one row per (licence_plate, fuel_sequence).** Not unique on `licence_plate` — see fan-out handling below.

32 columns as delivered. `describe raw.<table>` on landed data is treated as the source of truth for schema; discovery samples are a starting point only, since RDW populates different fuel-attribute columns depending on powertrain, and small samples do not reliably span all fuel types.

| Raw column | Staging column | Type (staged) | Notes |
|---|---|---|---|
| `kenteken` | `licence_plate` | varchar | FK to vehicles |
| `brandstof_volgnummer` | `fuel_sequence` | integer | 1 = primary fuel, 2+ = secondary/tertiary (hybrids, LPG conversions) |
| `brandstof_omschrijving` | `fuel_type` | varchar | Title-cased manually (`initcap` unavailable in DuckDB) |
| `co2_uitstoot_gecombineerd` | `co2_combined_gkm` | integer | gCO2/km |
| `co2_uitstoot_gewogen` | `co2_weighted_gkm` | integer | |
| `nettomaximumvermogen` | `net_max_power_kw` | decimal(10,2) | |
| `actieradius` | `range_km` | integer | |
| `actieradius_extern_oplaadbaar` | `electric_range_km` | integer | |
| `opgegeven_maximum_snelheid` | `declared_max_speed_kmh` | decimal(10,2) | |
| `emissiecode_omschrijving` | `emission_code` | varchar | |
| `uitlaatemissieniveau` | `euro_emission_standard` | varchar | |
| `klasse_hybride_elektrisch_voertuig` | `hybrid_class` | varchar | Independent cross-check for powertrain classification logic — confirmed consistent on hand-verified vehicles |

Columns present but unused (WLTP variants, noise-level fields): `emissie_co2_gecombineerd_wltp`, `brandstof_verbruik_gecombineerd_wltp`, `geluidsniveau_stationair`, `geluidsniveau_rijdend`, `toerental_geluidsniveau`, others. Out of scope for the current analysis.

**fuel_type distribution** (300K-vehicle extract, 359,438 fuel rows):

| fuel_type | rows | share |
|---|---:|---:|
| Benzine | 246,363 | 68.5% |
| Elektriciteit | 84,293 | 23.4% |
| Diesel | 26,607 | 7.4% |
| Lpg | 1,759 | 0.5% |
| Cng | 284 | 0.1% |
| Alcohol | 96 | <0.1% |
| Waterstof | 36 | <0.1% |

Electric row share (23.4%) is consistent with the vehicle-level fan-out rate (19.8%), cross-confirming the hybrid/electric population size via two independent counts.

---

## raw.body

**Grain: one row per (licence_plate, carrosserie_volgnummer).** ~1.3% of vehicles have no matching row — joins to this table must be LEFT, not INNER.

| Raw column | Staging column | Type (staged) |
|---|---|---|
| `kenteken` | `licence_plate` | varchar |
| `carrosserie_volgnummer` | `body_sequence` | integer |
| `type_carrosserie_europese_omschrijving` | `body_type` | varchar |
| `carrosserietype` | `body_type_code` | varchar |

---

## int_fuel_by_vehicle — resolving the fuel fan-out

**Problem:** `stg_fuel`'s grain (one row per fuel per vehicle) does not match the grain required downstream (one row per vehicle). A naive join between `stg_vehicles` and `stg_fuel` inflates row count from 300,000 to 359,438:

```sql
select count(*) from stg_vehicles v join stg_fuel f using (licence_plate);
-- 359438, not 300000
```

**Resolution:** aggregates `stg_fuel` to one row per `licence_plate`, combining fuel types into a `fuel_combination` label (`string_agg`, explicitly ordered for deterministic output across reruns) and deriving `powertrain_class` (BEV / Hybrid-PHEV / FCEV / ICE / Unknown) via a CASE expression that checks hydrogen first, to avoid misclassifying FCEVs that also carry an electric fuel row.

Handles 3+ fuel rows per vehicle by design, not just the expected 2 — the aggregation is generic over however many fuel rows a plate has, rather than assuming a fixed count. Example: a Toyota RAV4 in the dataset has three distinct fuel rows (Benzine, Elektriciteit, Lpg — a hybrid with an LPG conversion), correctly collapsed to one row with the correct classification.

**Powertrain distribution** (300,000 vehicles, zero Unknown):

| powertrain_class | count |
|---|---:|
| ICE | 215,707 |
| Hybrid / PHEV | 57,387 |
| BEV | 26,870 |
| FCEV | 36 |

FCEV count matches `Waterstof` fuel-type row count exactly. BEV + Hybrid/PHEV (84,257) is consistent with `Elektriciteit` fuel-type row count (84,293); the 36-row gap corresponds exactly to the FCEV count, indicating fuel-cell vehicles also carry an electric fuel row in the source — correctly handled by the hydrogen-first CASE ordering.

**Test:** `unique + not_null` on `licence_plate` — the load-bearing test that fails immediately if the fan-out is reintroduced. Verified the test catches its target failure mode directly: temporarily regrouped by `(licence_plate, fuel_sequence)` instead of `licence_plate` alone, confirmed the test failed, then reverted.

---

## int_vehicle_enriched and dim_brand

**`int_vehicle_enriched`** joins `stg_vehicles` to `int_fuel_by_vehicle` (safe — vehicle-grain, no fan-out risk) and `stg_body` (still fans out on `carrosserie_volgnummer`; resolved via `QUALIFY ROW_NUMBER() OVER (PARTITION BY licence_plate ORDER BY body_sequence) = 1`, selecting the primary entry rather than aggregating, since body variants don't carry independently meaningful information the way multiple fuel types do).

Both joins are **LEFT**, not INNER — an inner join to body would silently drop the ~1.3% of vehicles with no body record.

Derived flags:
- `is_import` — `true` if first admission date is more than 60 days before first NL registration date; `null` if either date is missing (explicitly distinguished from `false`, since a missing date makes the answer genuinely unknown, not negative)
- `apk_expired` — boolean, evaluated against `current_date`; value can change between runs even without new source data
- `is_exported` — `export_indicator = 'Ja'`

**`dim_brand`** — dimension table (Kimball sense): one row per brand, aggregated from `int_vehicle_enriched`. Surrogate key (`brand_sk`) via `dbt_utils.generate_surrogate_key`. All percentage columns guard their denominator with `nullif(..., 0)` to avoid producing NULL — and failing a downstream `not_null` test — on a zero-count group.

---

## fct_vehicle_registration and mart_fleet_electrification

**`fct_vehicle_registration`** — central fact table, incrementally materialized (`unique_key='vehicle_sk'`, `incremental_strategy='delete+insert'`). Filtered via `is_incremental()` against `max(_extracted_at)` already present in the table — a watermark pattern applied at the model layer, mirroring the same approach used in the extract script.

Idempotency verified directly: ran twice back-to-back with no new source data; row count identical after both runs.

**`mart_fleet_electrification`** — grain: one row per (registration_year, powertrain_class). Uses window functions for share-of-year (`SUM() OVER (PARTITION BY registration_year)`) and year-on-year change (`LAG() OVER (PARTITION BY powertrain_class ORDER BY registration_year)`).

**Resolved issue:** nested window functions (`LAG` wrapping `SUM() OVER (...)` directly) are illegal in SQL — all window functions in a query evaluate over the same result set, so one cannot depend on another's output within a single expression. Fixed by splitting into two CTEs: the base window aggregate materialized as a plain column first, with the second window function applied to that column in a separate subsequent step.

**Known limitation — uneven yearly vehicle counts:**

| Year | Count | Year | Count |
|---|---:|---|---:|
| 2010 | 13,380 | 2019 | 14,138 |
| 2011 | 15,452 | 2020 | **38,684** |
| 2012 | 15,406 | 2021 | 25,926 |
| 2013 | 12,919 | 2022 | 16,842 |
| 2014 | 12,977 | 2023 | 19,666 |
| 2015 | 12,418 | 2024 | **9,615** |
| 2016 | 19,859 | 2025 | **37,218** |
| 2017 | 20,535 | 2026 | 487 (partial year) |
| 2018 | 14,324 | | |

Most years fall in a 12,000–20,000 band. 2020 and 2025 are roughly double neighboring years; 2024 is the lowest of the entire 2010–2023 range. **Root cause:** the extract paginates via Socrata's `$order=:id`, an internal row identifier rather than a chronological field, so the fixed row-count cap produces a sample that is not proportional across registration years. This is a sampling artifact upstream of the model layer — `mart_fleet_electrification`'s SQL correctly computes shares of whatever sample it receives.

**Open decision:** either re-extract with per-year row bounding for a proportional sample, or retain the current sample and validate against external benchmarks on trend shape rather than absolute magnitude, with the caveat documented explicitly wherever the figures are published.

**Test:** `dbt_utils.unique_combination_of_columns` on `(registration_year, powertrain_class)` — the composite-grain assertion that would catch any regression of the upstream fan-out fix propagating through to a doubled percentage in the final KPI table.

---

## snap_vehicle_state — SCD Type 2

**Design:** `strategy='check'` against four tracked columns (`current_registration_date`, `apk_expiry_date`, `insured_indicator`, `export_indicator`) — the source provides no reliable `updated_at` column, ruling out the `timestamp` strategy. Selects directly from `source('rdw', 'vehicles')`, not a staging model, to avoid a snapshot/model build-order cycle (snapshots must run before regular models in a scheduled pipeline). Uses `hard_deletes='invalidate'` (dbt 1.9+ syntax; this project runs dbt 1.11.x).

**Verified end to end.** Manually updated one vehicle's APK expiry directly in `raw.vehicles`, reran the snapshot, and confirmed:

| licence_plate | apk_expiry_date | dbt_valid_from | dbt_valid_to |
|---|---|---|---|
| GZS78Z | 2029-01-15 | 2026-08-04 23:44:15.663416 | 2026-08-04 23:48:56.255295 |
| GZS78Z | 2030-01-01 | 2026-08-04 23:48:56.255295 | NULL |

The old row's `dbt_valid_to` and the new row's `dbt_valid_from` match exactly — a gapless, non-overlapping validity window, confirming the half-open interval `[valid_from, valid_to)` design behaves correctly at the transition point.

**Test:** `not_null` on `licence_plate` and `dbt_valid_from`. Deliberately **not** tested `unique` on `licence_plate` — a vehicle with tracked history legitimately has multiple rows (one per version); uniqueness here would be a modelling error, unlike every other model in this project.

**Implementation comparison — production Spark vs. this project's dbt snapshot:**

| | Hand-rolled (PySpark, production) | Declarative (dbt snapshot) |
|---|---|---|
| Approach | Hash tracked columns, MERGE against target, close previous row with an end timestamp, insert new version | Name unique key, strategy, tracked columns — dbt manages `dbt_valid_from`/`dbt_valid_to` and insert/close logic |
| Control | Full control over merge logic and performance tuning | Correct out of the box for a clean source with a small tracked-column set |
| Cost | Boilerplate to write and maintain; easy to get subtly wrong on late-arriving or out-of-order data | Minimal code; less flexible for complex merge conditions |
| Best fit | Merge condition is genuinely complex, volume needs partition-level tuning, or late-arriving data needs custom handling | Source is reasonably clean and the tracked-column set is small and stable |

---

## Known issues / decisions log

| Area | Issue | Resolution |
|---|---|---|
| Schema discovery | Single-row schema sample missed sparse columns (a trailer sample had no price/seats — Socrata omits null fields from JSON) | Discovery script rewritten to sample 50 rows and union keys across rows |
| Schema discovery | 50-row sample still under-covered `raw.fuel` (10/32 columns found); an incorrect substitute column was assumed for CO2 | Re-verified against `describe raw.fuel` on landed data; correct column restored |
| Extraction | Retry logic retried 404s (non-transient) alongside 429/5xx, due to both paths raising the same exception type | Branch explicitly on `status_code`; only retry 429/5xx |
| Staging | `initcap()` unavailable in DuckDB | Replaced with `upper(left(x,1)) \|\| lower(substr(x,2))` |
| Intermediate | Naive join between vehicles and fuel inflates row count 300,000 → 359,438 | Aggregated fuel to vehicle grain in `int_fuel_by_vehicle`; `unique+not_null` test on `licence_plate` guards against regression |
| Marts | Nested window functions (`LAG` wrapping `SUM() OVER`) — illegal in SQL | Split into two CTEs: base window aggregate as a plain column first, second window function applied to that column separately |
| Marts | Yearly vehicle counts uneven (2020/2025 ~2x neighboring years; 2024 lowest of 2010-2023 range) | Traced to `$order=:id` pagination — not chronological. Re-extraction vs. documented-caveat validation is an open decision |

---

## Open items

- Resolve the yearly-count sampling skew before validating against any external benchmark figure.
- Decide which CO2 field (`co2_uitstoot_gecombineerd` vs `co2_uitstoot_gewogen`) feeds any emissions-trend analysis.
- No owner geography in the register (privacy) — any "by region" analysis is out of scope.
- `snap_vehicle_state` currently lands in the default `main` schema, not following the `main_staging`/`main_intermediate`/`main_marts` convention used elsewhere. Add `+schema: snapshots` to `dbt_project.yml` for consistency, or confirm this is intentional before generating documentation.