"""Arbeitnow public job board API (Europe-focused, mostly Germany).
https://www.arbeitnow.com/api/job-board-api
"""

from __future__ import annotations

import time

import httpx

from ..models import RawPosting
from ..text import html_to_text, to_day

URL = "https://www.arbeitnow.com/api/job-board-api"


def parse(payload: dict) -> list[RawPosting]:
    postings = []
    for item in payload.get("data", []):
        if not item.get("slug") or not item.get("title"):
            continue
        postings.append(
            RawPosting(
                source="arbeitnow",
                source_id=item["slug"],
                url=item.get("url", ""),
                title=item["title"].strip(),
                company=(item.get("company_name") or "").strip(),
                location=(item.get("location") or "").strip(),
                posted_at=to_day(item.get("created_at")),
                description=html_to_text(item.get("description", "")),
                remote=item.get("remote"),
                tags=tuple(item.get("tags") or ()),
            )
        )
    return postings


def fetch(client: httpx.Client, pages: int = 3) -> list[RawPosting]:
    postings: list[RawPosting] = []
    url: str | None = URL
    for _ in range(pages):
        if not url:
            break
        response = client.get(url)
        response.raise_for_status()
        payload = response.json()
        postings.extend(parse(payload))
        url = (payload.get("links") or {}).get("next")
        time.sleep(1)  # be polite
    return postings
