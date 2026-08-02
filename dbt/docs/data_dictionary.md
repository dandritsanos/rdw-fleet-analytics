# Data Dictionary — RDW Fleet Analytics

Source: RDW Open Data (Socrata), `opendata.rdw.nl`. Extract script: `scripts/extract_rdw.py`.
Scope: passenger cars (`voertuigsoort = 'Personenauto'`), admission year 2010+.

Status: in development. Last extract 2026-07-31.

---

## Extract summary

| Metric | Value |
|---|---|
| Vehicles | 300,000 |
| Fuel rows | 359,438 |
| Body rows | 296,007 |
| Duration | 8m 17s |
| Fuel fan-out | 19.8% of vehicles have 2+ fuel rows (multi-fuel/hybrid) |
| Body coverage gap | 1.3% of vehicles have no body record |
| Pagination integrity | vehicle row count == distinct plate count at 300K scale (verified) |

---

## raw.vehicles

64 columns as delivered by the API. Selected subset used downstream:

| Raw column | Staging column | Type (staged) | Notes |
|---|---|---|---|
| `kenteken` | `licence_plate` | varchar | PK, not null enforced |
| `voertuigsoort` | `vehicle_type` | varchar | Filtered to `Personenauto` at extract time |
| `merk` | `brand` | varchar | Upper-cased |
| `handelsbenaming` | `trade_name` | varchar | |
| `inrichting` | `body_configuration` | varchar | Lower-cased |
| `eerste_kleur` | `primary_colour` | varchar | Upper-cased |
| `datum_eerste_toelating` | `first_admission_date` | date | YYYYMMDD string, parsed via `rdw_date` macro |
| `datum_eerste_tenaamstelling_in_nederland` | `first_nl_registration_date` | date | Used for `is_import` derivation, Day 6 |
| `datum_tenaamstelling` | `current_registration_date` | date | |
| `vervaldatum_apk` | `apk_expiry_date` | date | |
| `catalogusprijs` | `catalogue_price_eur` | decimal(12,2) | Absent on trailers/commercial vehicles — see discovery note below |
| `massa_ledig_voertuig` | `kerb_weight_kg` | integer | |
| `aantal_zitplaatsen` | `seat_count` | integer | |
| `aantal_cilinders` | `cylinder_count` | integer | |
| `cilinderinhoud` | `engine_displacement_cc` | integer | |
| `export_indicator` | `export_indicator` | varchar | Raw Ja/Nee, not boolean |
| `wam_verzekerd` | `insured_indicator` | varchar | Three states: Ja/Nee/N.v.t. — not boolean, see note |

**Note — `wam_verzekerd` is not boolean.** Register includes a third state (`N.v.t.`) for vehicle types where insurance status doesn't apply (e.g. trailers). Modelled as raw string, not cast to boolean.

**Note — `datum_*_dt` columns exist and are unused by design.** RDW provides pre-parsed ISO timestamp twins of every date field (e.g. `datum_tenaamstelling_dt`). Not used; dates are parsed from the raw `YYYYMMDD` string via the `rdw_date` macro instead, to keep parsing logic and failure handling under our control rather than dependent on the source's own conversion.

**Note — `api_gekentekende_voertuigen_*` columns.** Self-referential URLs to related Socrata datasets (assen, brandstof, carrosserie, etc.), not data fields. Not selected in staging.

---

## raw.fuel

**Grain: one row per (licence_plate, fuel_sequence).** Not unique on `licence_plate` — see fan-out below.

32 columns as delivered. Schema discovery history for this table:

| Stage | Columns found | Method |
|---|---|---|
| Day 1, initial | 10 | 50-row sample via `discover_schema.py` |
| Day 1, assumed mapping | — | Sample suggested `co2_emissieklasse` (class code) in place of the originally planned `co2_uitstoot_gecombineerd` (gCO2/km) |
| Day 4, actual | 32 | `describe raw.fuel` against the full 300K-row landed table |

The Day 1 sample was incomplete, not wrong in method — it under-covered the schema because RDW populates different fuel-attribute columns depending on powertrain, and 50 rows didn't span all fuel types. The Day 1 "correction" (`co2_emissieklasse`) turned out itself to be incorrect: the real column is `co2_uitstoot_gecombineerd`, matching the originally planned name. **`describe raw.<table>` on the landed data is the source of truth; discovery samples are a starting point only, not final.**

| Raw column | Staging column | Type (staged) | Notes |
|---|---|---|---|
| `kenteken` | `licence_plate` | varchar | FK to vehicles |
| `brandstof_volgnummer` | `fuel_sequence` | integer | 1 = primary fuel, 2 = secondary (hybrids) |
| `brandstof_omschrijving` | `fuel_type` | varchar | Title-cased manually (`initcap` unavailable in DuckDB) |
| `co2_uitstoot_gecombineerd` | `co2_combined_gkm` | integer | Real gCO2/km figure |
| `co2_uitstoot_gewogen` | `co2_weighted_gkm` | integer | |
| `nettomaximumvermogen` | `net_max_power_kw` | decimal(10,2) | |
| `actieradius` | `range_km` | integer | |
| `actieradius_extern_oplaadbaar` | `electric_range_km` | integer | |
| `opgegeven_maximum_snelheid` | `declared_max_speed_kmh` | decimal(10,2) | |
| `emissiecode_omschrijving` | `emission_code` | varchar | |
| `uitlaatemissieniveau` | `euro_emission_standard` | varchar | |
| `klasse_hybride_elektrisch_voertuig` | `hybrid_class` | varchar | Not in discovery sample; candidate cross-check for Day 5 powertrain logic |

Columns present but unused (WLTP variants, noise-level fields): `emissie_co2_gecombineerd_wltp`, `brandstof_verbruik_gecombineerd_wltp`, `geluidsniveau_stationair`, `geluidsniveau_rijdend`, `toerental_geluidsniveau`, others. Out of scope for the current analysis; not selected in staging.

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

**Grain: one row per (licence_plate, carrosserie_volgnummer).** ~1.3% of vehicles have no matching row — joins must be LEFT, not INNER.

| Raw column | Staging column | Type (staged) |
|---|---|---|
| `kenteken` | `licence_plate` | varchar |
| `carrosserie_volgnummer` | `body_sequence` | integer |
| `type_carrosserie_europese_omschrijving` | `body_type` | varchar |
| `carrosserietype` | `body_type_code` | varchar |


