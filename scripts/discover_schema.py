from __future__ import annotations
import os
import requests

DATASETS = {
    "vehicles": "m9d7-ebf2",
    "fuel": "8ys7-d773",
    "body": "vezc-m2t6",
}

headers = {"Accept": "application/json"}

if os.getenv("RDW_APP_TOKEN"):
    headers["X-App-Token"] = os.environ["RDW_APP_TOKEN"]

for name, ds_id in DATASETS.items():
    r = requests.get(
    f"https://opendata.rdw.nl/resource/{ds_id}.json",
        params={"$limit": 50, "$order": ":id",
                **({"$where": "voertuigsoort = 'Personenauto'"} if name == "vehicles" else {})},
        headers=headers, timeout=60,
    )
    rows = r.json()
    all_cols = {}
    for row in rows:
        for col, val in row.items():
            all_cols.setdefault(col, str(val)[:44])
    print(f"\n{'='*70}\n{name} ({ds_id}) - {len(all_cols)} columns across {len(rows)} rows\n{'='*70}")
    for col, val in sorted(all_cols.items()):
        print(f"  {col:<52} {val}")