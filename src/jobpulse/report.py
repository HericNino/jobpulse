"""Aggregates for the dashboard, computed with SQL over the in-memory database.

"Active" postings are the ones still listed in the last ACTIVE_DAYS days.
"""

from __future__ import annotations

import sqlite3
import statistics
from collections import defaultdict
from datetime import UTC, date, datetime

from .skills import CATEGORY

ACTIVE_DAYS = 14
TREND_SKILLS = 8
TREND_WEEKS = 12


def _rows(db: sqlite3.Connection, sql: str, *params) -> list[dict]:
    return [dict(row) for row in db.execute(sql, params)]


def build(db: sqlite3.Connection) -> dict:
    as_of = db.execute("select max(last_seen) from postings").fetchone()[0]
    if as_of is None:
        return {"as_of": None, "generated_at": _now(), "summary": {"active": 0}}

    date.fromisoformat(as_of)  # guard: it's interpolated into the view below
    db.execute("drop view if exists active")
    db.execute(f"create temp view active as select * from postings where last_seen >= date('{as_of}', '-{ACTIVE_DAYS} days')")
    active = db.execute("select count(*) from active").fetchone()[0]

    summary = {
        "active": active,
        "new_this_week": db.execute("select count(*) from postings where first_seen > date(?, '-7 days')", (as_of,)).fetchone()[0],
        "companies": db.execute("select count(distinct company) from active").fetchone()[0],
        "remote_share": _share(db, "select count(*) from active where remote = 'remote'", active),
        "salary_share": _share(db, "select count(*) from active where salary_min is not null", active),
        "all_time": db.execute("select count(*) from postings").fetchone()[0],
    }

    top_skills = _rows(
        db,
        """
        select ps.skill, count(*) as postings, count(distinct a.company) as companies
        from posting_skills ps join active a on a.id = ps.posting_id
        group by ps.skill
        order by postings desc, ps.skill
        limit 30
        """,
    )
    for row in top_skills:
        row["share"] = round(row["postings"] / active, 4) if active else 0
        row["category"] = CATEGORY.get(row["skill"], "Other")

    return {
        "as_of": as_of,
        "generated_at": _now(),
        "active_days": ACTIVE_DAYS,
        "summary": summary,
        "top_skills": top_skills,
        "trend": _trend(db, [r["skill"] for r in top_skills[:TREND_SKILLS]], as_of),
        "pairs": _rows(
            db,
            """
            select a.skill as a, b.skill as b, count(*) as postings
            from posting_skills a
            join posting_skills b on a.posting_id = b.posting_id and a.skill < b.skill
            join active p on p.id = a.posting_id
            group by a.skill, b.skill
            having count(*) >= 2
            order by postings desc
            limit 600
            """,
        ),
        "seniority": _rows(db, "select seniority as key, count(*) as postings from active group by seniority order by postings desc"),
        "work_mode": _rows(db, "select remote as key, count(*) as postings from active group by remote order by postings desc"),
        "companies": _rows(
            db,
            """
            select company, count(*) as postings from active where company != ''
            group by company order by postings desc, company limit 12
            """,
        ),
        "sources": _rows(db, "select source, count(*) as postings from active group by source order by postings desc"),
        "salaries": _salaries(db),
    }


def _trend(db: sqlite3.Connection, skills: list[str], as_of: str) -> dict:
    """Weekly share of new postings mentioning each skill, for complete weeks (Monday to Sunday)."""
    weeks = _rows(
        db,
        """
        select date(first_seen, 'weekday 0', '-6 days') as week, count(*) as total
        from postings
        where first_seen > date(?, ?)
        group by week
        having date(week, '+6 days') <= ?  -- only finished weeks
        order by week
        """,
        as_of,
        f"-{(TREND_WEEKS + 1) * 7} days",
        as_of,
    )
    if not skills or not weeks:
        return {"weeks": [], "series": []}
    marks = ",".join("?" * len(skills))
    counts = {
        (r["week"], r["skill"]): r["n"]
        for r in _rows(
            db,
            f"""
            select date(p.first_seen, 'weekday 0', '-6 days') as week, ps.skill, count(*) as n
            from postings p join posting_skills ps on ps.posting_id = p.id
            where ps.skill in ({marks})
            group by week, ps.skill
            """,
            *skills,
        )
    }
    return {
        "weeks": [{"week": w["week"], "total": w["total"]} for w in weeks],
        "series": [{"skill": s, "share": [round(counts.get((w["week"], s), 0) / w["total"], 4) for w in weeks]} for s in skills],
    }


def _salaries(db: sqlite3.Connection) -> dict:
    """Yearly pay where it is stated, per currency, overall and per skill (at least 3 postings)."""
    rows = _rows(
        db,
        """
        select p.id, p.salary_min, p.salary_max, p.salary_currency, p.salary_period, ps.skill
        from active p left join posting_skills ps on ps.posting_id = p.id
        where p.salary_currency is not null and p.salary_period in ('year', 'month')
          and coalesce(p.salary_min, p.salary_max) is not null
        """,
    )
    overall: dict[str, dict[str, int]] = defaultdict(dict)
    by_skill: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r in rows:
        low = r["salary_min"] or r["salary_max"]
        high = r["salary_max"] or r["salary_min"]
        yearly = (low + high) / 2 * (12 if r["salary_period"] == "month" else 1)
        if not 5_000 <= yearly <= 1_000_000:  # drop obvious parsing mistakes
            continue
        overall[r["salary_currency"]][r["id"]] = round(yearly)
        if r["skill"]:
            by_skill[(r["salary_currency"], r["skill"])].append(round(yearly))

    result = {}
    for currency, values in overall.items():
        mids = sorted(values.values())
        if len(mids) < 3:
            continue
        result[currency] = {
            "postings": len(mids),
            **_quartiles(mids),
            "by_skill": sorted(
                (
                    {"skill": s, "postings": len(v), "median": round(statistics.median(v))}
                    for (c, s), v in by_skill.items()
                    if c == currency and len(v) >= 3
                ),
                key=lambda x: -x["median"],
            ),
        }
    return result


def _quartiles(values: list[int]) -> dict:
    q1, q2, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return {"p25": round(q1), "median": round(q2), "p75": round(q3)}


def _share(db: sqlite3.Connection, sql: str, total: int) -> float:
    return round(db.execute(sql).fetchone()[0] / total, 4) if total else 0.0


def _now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()
