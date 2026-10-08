"""Job sources. Each module exposes `parse(payload) -> list[RawPosting]` (pure,
tested against saved fixtures) and `fetch(client, pages) -> list[RawPosting]`
(network). Only sources with a public API meant for this kind of use go here.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx

from ..models import RawPosting
from . import arbeitnow, remotive

Fetcher = Callable[[httpx.Client, int], list[RawPosting]]

SOURCES: dict[str, Fetcher] = {
    "arbeitnow": arbeitnow.fetch,
    "remotive": remotive.fetch,
}

USER_AGENT = "jobpulse/0.1 (+https://github.com/HericNino/jobpulse)"


def make_client() -> httpx.Client:
    return httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
