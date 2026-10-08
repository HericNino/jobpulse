from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .extract import Analysis, analyze_keywords
from .models import Posting, RawPosting
from .skills import is_tech
from .store import new_posting

log = logging.getLogger(__name__)

MAX_FAILURES_IN_A_ROW = 3


@dataclass
class MergeStats:
    seen: int = 0
    new: int = 0
    skipped: int = 0  # not tech roles
    analyzed_by_model: int = 0


def merge(
    existing: dict[str, Posting],
    fetched: Iterable[RawPosting],
    today: str,
    analyze: Callable[[RawPosting], Analysis | None] | None = None,
    max_model_calls: int = 0,
) -> MergeStats:
    """Add new postings and refresh `last_seen` on known ones, in place.

    Known postings are never re-analyzed. New ones go to `analyze` (Claude)
    while the budget lasts, and to the keyword matcher otherwise or on failure.
    """
    stats = MergeStats()
    failures_in_a_row = 0
    for raw in fetched:
        stats.seen += 1
        known = existing.get(raw.id)
        if known:
            known.last_seen = max(known.last_seen, today)
            continue

        analysis = None
        # don't spend model calls on postings that are clearly not tech roles
        if analyze and stats.analyzed_by_model < max_model_calls and is_tech(raw.title, analyze_keywords(raw).skills):
            try:
                analysis = analyze(raw)
                failures_in_a_row = 0
            except Exception as error:  # keep the run going; keywords are a fine fallback
                log.warning("model analysis failed for %s: %s", raw.id, error)
                failures_in_a_row += 1
                if failures_in_a_row >= MAX_FAILURES_IN_A_ROW:
                    log.error(
                        "model failed %d times in a row (bad key? outage?); keywords only for the rest of this run", failures_in_a_row
                    )
                    analyze = None
            if analysis:
                stats.analyzed_by_model += 1
        keywords = analyze_keywords(raw)
        if not is_tech(raw.title, (analysis or keywords).skills):
            stats.skipped += 1
            continue
        existing[raw.id] = new_posting(raw, analysis or keywords, today)
        stats.new += 1
    return stats


def dedupe(raws: Iterable[RawPosting]) -> list[RawPosting]:
    seen: dict[str, RawPosting] = {}
    for raw in raws:
        seen.setdefault(raw.id, raw)
    return list(seen.values())


def prune(postings: dict[str, Posting]) -> int:
    """Drop stored postings that the current rules no longer count as tech roles."""
    gone = [key for key, p in postings.items() if not is_tech(p.title, p.skills)]
    for key in gone:
        del postings[key]
    return len(gone)
