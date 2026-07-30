from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger(__name__)

BASE = "https://opendata.rdw.nl/resource"


def _session() -> requests.Session:
    """Build a requests session with the app token attached, if present."""
    s = requests.Session()
    s.headers["Accept"] = "application/json"
    token = os.getenv("RDW_APP_TOKEN")
    if token:
        s.headers["X-App-Token"] = token
    else:
        log.warning("No RDW_APP_TOKEN set - you are on the shared anonymous rate limit.")
    return s


import time


def _get(session: requests.Session, ds_id: str, params: dict, tries: int = 5) -> list[dict]:
    """GET one page with exponential backoff. Honours 429 and transient 5xx.

    Only status codes that are likely transient (429 rate-limited, 5xx
    server error) get retried. Any other error status - most commonly a
    404 for a bad dataset ID, or 400 for a malformed query - fails
    immediately, since retrying a request that is wrong will just
    reproduce the same failure five times and delay finding the real bug.
    """
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



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    s = _session()
    try:
        _get(s, "totally-fake-id", {"$limit": 1})
    except requests.RequestException as e:
        print(f"Failed as expected (no retries on 4xx): {e}")