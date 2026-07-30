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


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    s = _session()
    print(s.headers)