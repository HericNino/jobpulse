"""Remotive public API (remote jobs). Their terms ask for a link back to the
original posting and no more than a few requests a day, which this respects.
https://remotive.com/api/remote-jobs
"""

from __future__ import annotations

import httpx

from ..models import RawPosting
from ..text import html_to_text, to_day

URL = "https://remotive.com/api/remote-jobs"
CATEGORIES = ["software-dev", "data", "devops"]


def parse(payload: dict) -> list[RawPosting]:
    postings = []
    for item in payload.get("jobs", []):
        if not item.get("id") or not item.get("title"):
            continue
        postings.append(
            RawPosting(
                source="remotive",
                source_id=str(item["id"]),
                url=item.get("url", ""),
                title=item["title"].strip(),
                company=(item.get("company_name") or "").strip(),
                location=(item.get("candidate_required_location") or "").strip(),
                posted_at=to_day(item.get("publication_date")),
                description=html_to_text(item.get("description", "")),
                remote=True,
                tags=tuple(item.get("tags") or ()),
                salary_text=(item.get("salary") or "").strip() or None,
            )
        )
    return postings


def fetch(client: httpx.Client, pages: int = 3) -> list[RawPosting]:
    # one request per category; `pages` doesn't apply to this API
    postings: list[RawPosting] = []
    for category in CATEGORIES:
        response = client.get(URL, params={"category": category})
        response.raise_for_status()
        postings.extend(parse(response.json()))
    return postings
