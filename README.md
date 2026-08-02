# In active development


## Extract performance (2026-07-31)
- Full bounded extract: 300,000 vehicles + satellites, admission year 2010+, passenger cars only
- Duration: 8m 17s
- Fuel fan-out: 359,438 rows for 300,000 vehicles (~19.8% of vehicles have 2+ fuel types)
- Body coverage: 296,007 / 300,000 vehicles have a body record (~1.3% gap, consistent with register data quality)
- Verified: vehicle rows == distinct plates (no pagination duplicates at scale)