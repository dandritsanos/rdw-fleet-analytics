## Schema deltas vs plan

Catalogusprijs, seats, cylinders, displacement: all present in vehicles table.
  (First single-row sample missed them. It happened to be a trailer, which has
  no price/seats, and Socrata omits null fields from JSON.)

Fuel table has different column names than originally planned:
    nettomaximumvermogen          -> unchanged, use as-is (net power, kW)
    co2_emissieklasse             -> use instead of co2_uitstoot_gecombineerd (now a class code, not gCO2/km)
    actieradius_extern_oplaadbaar -> use instead of actie_radius_extern_opladen (electric range, km)
    actieradius                   -> new: general range, km
    opgegeven_maximum_snelheid    -> new: declared max speed
    uitlaatemissieniveau          -> new: EURO emission standard


api_gekentekende_voertuigen_* columns are just links to other datasets, not data —> ignore them.