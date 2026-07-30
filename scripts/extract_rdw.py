from __future__ import annotations

import logging
import os
import time

import requests

log = logging.getLogger(__name__)

BASE = "https://opendata.rdw.nl/resource"
VEHICLES = "m9d7-ebf2"


def _session() -> requests.Session:
    """Build a requests session with the app token attached."""
    s = requests.Session()
    s.headers["Accept"] = "application/json"
    token = os.getenv("RDW_APP_TOKEN")
    if token:
        s.headers["X-App-Token"] = token
    else:
        log.warning("No RDW_APP_TOKEN set - you are on the shared anonymous rate limit.")
    return s


def _get(session: requests.Session, ds_id: str, params: dict, tries: int = 5) -> list[dict]:
    url = f"{BASE}/{ds_id}.json"
    for attempt in range(1, tries + 1):
        resp = session.get(url, params=params, timeout=120)

        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == tries:
                log.error("giving up on %s after %s attempts", ds_id, tries)
                resp.raise_for_status()
            wait = min(60, 2 ** attempt)
            log.warning(
                "attempt %s/%s got HTTP %s; retrying in %ss",
                attempt, tries, resp.status_code, wait,
            )
            time.sleep(wait)
            continue

        # any other status (including a real 4xx, or success) is final -
        # do not retry, let it raise or return immediately
        resp.raise_for_status()
        return resp.json()

    return []


def _paginate(session: requests.Session, ds_id: str, where: str | None = None,
               max_rows: int = 5000, page_size: int = 5000) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while len(out) < max_rows:
        params = {
            "$limit": min(page_size, max_rows - len(out)),
            "$offset": offset,
            "$order": ":id",
        }
        if where:
            params["$where"] = where
        page = _get(session, ds_id, params)
        if not page:
            break
        out.extend(page)
        offset += len(page)
        log.info("%s: %s rows fetched", ds_id, f"{len(out):,}")
        if len(page) < params["$limit"]:
            break  # short page = end of the result set
    return out


import os
from datetime import datetime, timezone

import duckdb
import pandas as pd

DB_PATH = "dbt/data/rdw.duckdb"


def _land(con: duckdb.DuckDBPyConnection, table: str, rows: list[dict], extracted_at: datetime) -> int:
    """Write rows into the raw schema, as strings, unmodified."""
    if not rows:
        log.info("raw.%s: nothing to land", table)
        return 0
    df = pd.DataFrame(rows).astype("string")
    df["_extracted_at"] = extracted_at
    con.register("incoming", df)
    con.execute(f"create or replace table raw.{table} as select * from incoming")
    con.unregister("incoming")
    n = con.execute(f"select count(*) from raw.{table}").fetchone()[0]
    log.info("raw.%s: %s rows landed", table, f"{n:,}")
    return n



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    s = _session()
    rows = _paginate(s, VEHICLES, where="voertuigsoort = 'Personenauto'", max_rows=5000)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = duckdb.connect(DB_PATH)
    con.execute("create schema if not exists raw")
    _land(con, "vehicles", rows, datetime.now(timezone.utc))
    con.close()