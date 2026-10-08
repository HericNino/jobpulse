"""Storage: data/postings.jsonl is the source of truth (one posting per line,
sorted by id, so daily git diffs stay small and readable). For reporting it is
loaded into an in-memory SQLite database.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
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


SCHEMA = """
create table postings (
  id text primary key,
  source text not null,
  title text not null,
  company text,
  country text,
  remote text,
  seniority text,
  posted_at text,
  first_seen text not null,
  last_seen text not null,
  salary_min integer,
  salary_max integer,
  salary_currency text,
  salary_period text
);
create table posting_skills (
  posting_id text not null references postings(id),
  skill text not null,
  primary key (posting_id, skill)
);
create index posting_skills_skill on posting_skills(skill);
"""


def to_sqlite(postings: Iterable[Posting]) -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    for p in postings:
        db.execute(
            "insert into postings values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                p.id,
                p.source,
                p.title,
                p.company,
                p.country,
                p.remote,
                p.seniority,
                p.posted_at,
                p.first_seen,
                p.last_seen,
                p.salary_min,
                p.salary_max,
                p.salary_currency,
                p.salary_period,
            ),
        )
        db.executemany("insert into posting_skills values (?, ?)", [(p.id, s) for s in set(p.skills)])
    return db
