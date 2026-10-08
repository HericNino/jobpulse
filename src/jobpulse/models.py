from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Remote = Literal["remote", "hybrid", "onsite", "unknown"]
Seniority = Literal["intern", "junior", "mid", "senior", "lead", "unknown"]


@dataclass(frozen=True)
class RawPosting:
    """A posting as fetched from a source, before analysis.

    `description` is only held in memory during a run. It is never written to
    disk, so the repository stores facts about postings, not copies of them.
    """

    source: str
    source_id: str
    url: str
    title: str
    company: str
    location: str
    posted_at: str  # YYYY-MM-DD
    description: str
    remote: bool | None = None
    tags: tuple[str, ...] = ()
    salary_text: str | None = None

    @property
    def id(self) -> str:
        return f"{self.source}:{self.source_id}"


@dataclass
class Posting:
    """What we keep about a posting, one line per posting in data/postings.jsonl."""

    id: str
    source: str
    url: str
    title: str
    company: str
    location: str
    country: str | None
    posted_at: str
    first_seen: str
    last_seen: str
    remote: Remote = "unknown"
    seniority: Seniority = "unknown"
    skills: list[str] = field(default_factory=list)
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    salary_period: Literal["year", "month", "hour"] | None = None
    analyzed_by: str = "keywords"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Posting:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})
