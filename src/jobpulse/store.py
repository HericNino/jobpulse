"""Storage: data/postings.jsonl is the source of truth, one posting per line,
sorted by id so daily git diffs stay small and readable. Reporting reads the
same file with DuckDB (see transform/).
"""

from __future__ import annotations

import json
from pathlib import Path

from .extract import Analysis
from .models import Posting, RawPosting


def load(path: Path) -> dict[str, Posting]:
    if not path.exists():
        return {}
    postings = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            posting = Posting.from_dict(json.loads(line))
            postings[posting.id] = posting
    return postings


def save(path: Path, postings: dict[str, Posting]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(postings[key].to_dict(), ensure_ascii=False, sort_keys=True) for key in sorted(postings)]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def new_posting(raw: RawPosting, analysis: Analysis, today: str) -> Posting:
    return Posting(
        id=raw.id,
        source=raw.source,
        url=raw.url,
        title=raw.title,
        company=raw.company,
        location=raw.location,
        country=analysis.country,
        posted_at=raw.posted_at,
        first_seen=today,
        last_seen=today,
        remote=analysis.remote,
        seniority=analysis.seniority,
        skills=analysis.skills,
        salary_min=analysis.salary_min,
        salary_max=analysis.salary_max,
        salary_currency=analysis.salary_currency,
        salary_period=analysis.salary_period,
        analyzed_by=analysis.analyzed_by,
    )
