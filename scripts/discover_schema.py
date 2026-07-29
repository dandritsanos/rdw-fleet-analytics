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
        params={"$limit": 1, "$order": ":id"},
        headers=headers,
        timeout=60
    )

    r.raise_for_status()
    rows = r.json()
    print(f"\n{'=' * 70}\n{name} ({ds_id}) - {len(rows[0]) if rows else 0} columns\n{'-' * 70}")
    for col, val in sorted(rows[0].items()):
        sample = str(val)[:44]
        print(f" {col:<48} {sample}")