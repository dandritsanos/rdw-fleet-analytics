from __future__ import annotations

import logging
import os
import time

import requests
from datetime import datetime, timezone

import duckdb
import pandas as pd

log = logging.getLogger(__name__)

BASE = "https://opendata.rdw.nl/resource"
VEHICLES = "m9d7-ebf2"
DB_PATH = "dbt/data/rdw.duckdb"


def _session() -> requests.Session:
    """Build a requests session with the app token attached."""
    s = requests.Session()
    s.headers["Accept"] = "application/json"
    token = os.getenv("RDW_APP_TOKEN")
    if token:
        s.headers["X-App-Token"] = token
    else:
        log.warning(
            "No RDW_APP_TOKEN set - you are on the shared anonymous rate limit."
        )
    return s


def _get(
    session: requests.Session, ds_id: str, params: dict, tries: int = 5
) -> list[dict]:
    url = f"{BASE}/{ds_id}.json"
    for attempt in range(1, tries + 1):
        resp = session.get(url, params=params, timeout=120)

        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == tries:
                log.error("giving up on %s after %s attempts", ds_id, tries)
                resp.raise_for_status()
            wait = min(60, 2**attempt)
            log.warning(
                "attempt %s/%s got HTTP %s; retrying in %ss",
                attempt,
                tries,
                resp.status_code,
                wait,
            )
            time.sleep(wait)
            continue

        resp.raise_for_status()
        return resp.json()

    return []


def _paginate(
    session: requests.Session,
    ds_id: str,
    where: str | None = None,
    max_rows: int = 5000,
    page_size: int = 5000,
) -> list[dict]:
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


def _land(
    con: duckdb.DuckDBPyConnection, table: str, rows: list[dict], extracted_at: datetime
) -> int:
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


FUEL = "8ys7-d773"
BODY = "vezc-m2t6"
PLATE_BATCH = 400   # plates per IN() lookup - keeps URLs under length limits


def _fetch_by_plates(session: requests.Session, ds_id: str, plates: list[str]) -> list[dict]:
    """Fetch satellite rows only for the plates we actually landed.

    The fuel and body datasets cover the entire national fleet. Rather
    than downloading millions of rows to use a few thousand, this asks
    the API for rows matching our specific plates via a SoQL IN() filter,
    batched at 400 plates per request to stay under URL length limits.
    """
    rows: list[dict] = []
    for i in range(0, len(plates), PLATE_BATCH):
        batch = plates[i:i + PLATE_BATCH]
        quoted = ",".join(f"'{p}'" for p in batch)
        rows.extend(
            _paginate(session, ds_id,
                      where=f"kenteken in({quoted})",
                      max_rows=len(batch) * 5)   # generous ceiling; hybrids have 2+ fuel rows
        )
        log.info("%s: %s/%s plates looked up", ds_id, min(i + PLATE_BATCH, len(plates)), len(plates))
    return rows

def _get_watermark(con: duckdb.DuckDBPyConnection) -> str | None:
    """Newest registration date already landed. None on a cold start.

    Used to build an incremental $where filter so reruns only fetch rows
    newer than what we already have. Known limitation, accepted for this
    project: a watermark cannot detect deletions (e.g. an exported
    vehicle leaving the register) - that requires CDC or a full diff.
    """
    try:
        return con.execute(
            "select max(datum_tenaamstelling) from raw.vehicles"
        ).fetchone()[0]
    except duckdb.Error:
        return None   # table doesn't exist yet - cold start

MAX_ROWS = int(os.getenv("RDW_MAX_ROWS", "300000"))
MIN_ADMISSION_YEAR = os.getenv("RDW_MIN_ADMISSION_YEAR", "2010")


def run_extract() -> dict[str, int]:
    """Full extract: vehicles (bounded, watermarked) then satellites by plate."""
    extracted_at = datetime.now(timezone.utc)
    session = _session()
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = duckdb.connect(DB_PATH)
    con.execute("create schema if not exists raw")

    where = (
        f"datum_eerste_toelating >= '{MIN_ADMISSION_YEAR}0101'"
        " AND voertuigsoort = 'Personenauto'"
    )
    watermark = _get_watermark(con)
    print(f"DEBUG: watermark = {watermark!r}, DB_PATH = {DB_PATH!r}")
    if watermark:
        where += f" AND datum_tenaamstelling > '{watermark}'"
        log.info("incremental run from watermark %s", watermark)
    else:
        log.info("cold start - full bounded load")

    vehicles = _paginate(session, VEHICLES, where=where, max_rows=MAX_ROWS)
    if not vehicles:
        log.info("no new vehicles; nothing to do")
        con.close()
        return {"vehicles": 0, "fuel": 0, "body": 0}

    plates = sorted({r["kenteken"] for r in vehicles if r.get("kenteken")})
    log.info("fetching satellites for %s plates", f"{len(plates):,}")

    counts = {
        "vehicles": _land(con, "vehicles", vehicles, extracted_at),
        "fuel":     _land(con, "fuel", _fetch_by_plates(session, FUEL, plates), extracted_at),
        "body":     _land(con, "body", _fetch_by_plates(session, BODY, plates), extracted_at),
    }
    con.close()
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print(run_extract())