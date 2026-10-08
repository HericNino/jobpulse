"""Builds data/report.json.

The numbers are defined as dbt models in transform/ (SQL, run on DuckDB, with
data tests). This module runs `dbt build` against data/postings.jsonl and
reshapes the resulting tables into the JSON the dashboard reads.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb

TRANSFORM_DIR = Path(__file__).resolve().parents[2] / "transform"
ACTIVE_DAYS = 14


class DbtError(RuntimeError):
    pass


def run_dbt(postings_path: Path, warehouse: Path, active_days: int = ACTIVE_DAYS) -> None:
    """Run `dbt build` (models and data tests). Raises DbtError if anything fails."""
    from dbt.cli.main import dbtRunner  # imported lazily: dbt is slow to import

    state = warehouse.parent / "dbt"
    args = [
        "build",
        "--project-dir",
        str(TRANSFORM_DIR),
        "--profiles-dir",
        str(TRANSFORM_DIR),
        "--target-path",
        str(state / "target"),
        "--log-path",
        str(state / "logs"),
        "--vars",
        json.dumps({"postings_path": str(postings_path.resolve()), "active_days": active_days}),
        "--quiet",
    ]
    previous = os.environ.get("JOBPULSE_WAREHOUSE")
    os.environ["JOBPULSE_WAREHOUSE"] = str(warehouse)  # read by transform/profiles.yml
    try:
        result = dbtRunner().invoke(args)
    finally:
        if previous is None:
            os.environ.pop("JOBPULSE_WAREHOUSE", None)
        else:
            os.environ["JOBPULSE_WAREHOUSE"] = previous
    if not result.success:
        raise DbtError(f"dbt build failed: {result.exception or 'see the dbt output above'}")


def build(postings_path: Path, active_days: int = ACTIVE_DAYS) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        warehouse = Path(tmp) / "warehouse.duckdb"
        run_dbt(postings_path, warehouse, active_days)
        with duckdb.connect(str(warehouse)) as db:  # same config as the dbt connection in this process
            return _assemble(db, active_days)


def _rows(db: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> list[dict]:
    cursor = db.execute(sql, params or [])
    names = [d[0] for d in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _assemble(db: duckdb.DuckDBPyConnection, active_days: int) -> dict:
    summary = _rows(db, "select * from mart_summary")[0]
    as_of = summary.pop("as_of")
    if as_of is None:
        return {"as_of": None, "generated_at": _now(), "summary": {"active": 0}}

    for key in ("remote_share", "salary_share"):
        summary[key] = round(summary[key], 4)

    top_skills = _rows(db, "select skill, postings, companies, share, category from mart_top_skills limit 30")
    for row in top_skills:
        row["share"] = round(row["share"], 4)

    trend_rows = _rows(db, "select week, total, skill, share from mart_weekly_trend order by rank, week")
    weeks = sorted({(r["week"], r["total"]) for r in trend_rows})
    series: dict[str, list[float]] = {}
    for r in trend_rows:
        series.setdefault(r["skill"], []).append(round(r["share"], 4))

    breakdowns = _rows(db, "select dimension, key, postings from mart_breakdowns order by postings desc, key")

    def breakdown(dimension: str, name: str = "key") -> list[dict]:
        return [{name: r["key"], "postings": r["postings"]} for r in breakdowns if r["dimension"] == dimension]

    salaries = {}
    for row in _rows(db, "select currency, postings, p25, median, p75 from mart_salaries order by currency"):
        currency = row.pop("currency")
        by_skill = _rows(db, "select skill, postings, median from mart_salaries_by_skill where currency = ?", [currency])
        salaries[currency] = {
            **{k: int(v) for k, v in row.items()},
            "by_skill": [{"skill": r["skill"], "postings": r["postings"], "median": int(r["median"])} for r in by_skill],
        }

    return {
        "as_of": _iso(as_of),
        "generated_at": _now(),
        "active_days": active_days,
        "summary": summary,
        "top_skills": top_skills,
        "trend": {
            "weeks": [{"week": _iso(w), "total": t} for w, t in weeks],
            "series": [{"skill": skill, "share": shares} for skill, shares in series.items()],
        },
        "pairs": _rows(db, "select a, b, postings from mart_skill_pairs limit 600"),
        "seniority": breakdown("seniority"),
        "work_mode": breakdown("work_mode"),
        "companies": _rows(db, "select company, postings from mart_companies limit 12"),
        "sources": breakdown("source", "source"),
        "salaries": salaries,
    }


def _iso(value: date | str) -> str:
    return value.isoformat() if isinstance(value, date) else str(value)


def _now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()
