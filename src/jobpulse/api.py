"""Read-only HTTP API over the dbt marts.

The warehouse file is built ahead of time (`jobpulse warehouse`, or during the Docker
build) and opened read-only, so the API never touches the source data or the network.

    uvicorn jobpulse.api:create_app --factory
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .skills import canonical

Seniority = Literal["intern", "junior", "mid", "senior", "lead", "unknown"]
WorkMode = Literal["remote", "hybrid", "onsite", "unknown"]


class Health(BaseModel):
    status: Literal["ok"]
    as_of: date | None
    active_postings: int


class Summary(BaseModel):
    as_of: date | None
    active: int
    new_this_week: int
    companies: int
    remote_share: float
    salary_share: float
    all_time: int


class Skill(BaseModel):
    skill: str
    category: str
    postings: int
    companies: int
    share: float


class Companion(BaseModel):
    skill: str
    postings: int
    share: float  # of the postings that mention the requested skill


class WeekShare(BaseModel):
    week: date
    share: float


class SkillMedianPay(BaseModel):
    currency: str
    postings: int
    median: float


class SkillDetail(Skill):
    companions: list[Companion]
    trend: list[WeekShare]
    pay: list[SkillMedianPay]


class Company(BaseModel):
    company: str
    postings: int


class Posting(BaseModel):
    id: str
    title: str
    company: str | None
    url: str | None
    seniority: str
    work_mode: str
    first_seen: date
    skills: list[str]


def create_app(warehouse: Path | None = None) -> FastAPI:
    path = Path(warehouse or os.environ.get("JOBPULSE_WAREHOUSE", ".dbt/warehouse.duckdb"))
    state: dict[str, duckdb.DuckDBPyConnection] = {}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if not path.exists():
            raise RuntimeError(f"warehouse not found at {path}; build it with `jobpulse warehouse`")
        state["db"] = duckdb.connect(str(path), read_only=True)
        yield
        state.pop("db").close()

    app = FastAPI(
        title="jobpulse",
        version="0.1.0",
        description="Which skills tech job postings ask for. Data is refreshed daily; see `as_of` on /health.",
        lifespan=lifespan,
    )
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])

    def rows(sql: str, *params) -> list[dict]:
        cursor = state["db"].cursor()  # one cursor per request: safe across threads
        try:
            result = cursor.execute(sql, list(params))
            names = [d[0] for d in result.description]
            return [dict(zip(names, row, strict=True)) for row in result.fetchall()]
        finally:
            cursor.close()

    @app.get("/health", response_model=Health)
    def health():
        summary = rows("select as_of, active from mart_summary")[0]
        return {"status": "ok", "as_of": summary["as_of"], "active_postings": summary["active"]}

    @app.get("/summary", response_model=Summary)
    def summary():
        return rows("select * from mart_summary")[0]

    @app.get("/skills", response_model=list[Skill])
    def skills(
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        category: Annotated[str | None, Query(description="e.g. Frontend, Data, Cloud & DevOps")] = None,
    ):
        if category:
            return rows(
                "select * from mart_top_skills where lower(category) = lower(?) order by postings desc, skill limit ?", category, limit
            )
        return rows("select * from mart_top_skills order by postings desc, skill limit ?", limit)

    @app.get("/skills/{name}", response_model=SkillDetail, responses={404: {"description": "No active postings mention this skill"}})
    def skill(name: str):
        found = rows("select * from mart_top_skills where lower(skill) = lower(?)", canonical(name) or name)
        if not found:
            raise HTTPException(404, f"no active postings mention {name!r}")
        detail = found[0]
        detail["companions"] = rows(
            """
            select case when a = ? then b else a end as skill, postings, postings / ? as share
            from mart_skill_pairs where ? in (a, b)
            order by postings desc, skill limit 10
            """,
            detail["skill"],
            detail["postings"],
            detail["skill"],
        )
        detail["trend"] = rows("select week, share from mart_weekly_trend where skill = ? order by week", detail["skill"])
        detail["pay"] = rows(
            "select currency, postings, median from mart_salaries_by_skill where skill = ? order by postings desc", detail["skill"]
        )
        return detail

    @app.get("/companies", response_model=list[Company])
    def companies(limit: Annotated[int, Query(ge=1, le=100)] = 20):
        return rows("select company, postings from mart_companies order by postings desc, company limit ?", limit)

    @app.get("/postings", response_model=list[Posting])
    def postings(
        skill: str | None = None,
        seniority: Seniority | None = None,
        work_mode: WorkMode | None = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ):
        """Active postings, newest first. Filters combine with AND."""
        wanted = canonical(skill) or skill if skill else None
        return rows(
            """
            select
                p.posting_id as id, p.title, p.company, p.url, p.seniority, p.work_mode, p.first_seen,
                coalesce(list_sort(list(s.skill) filter (where s.skill is not null)), []) as skills
            from active_postings p
            left join stg_posting_skills s using (posting_id)
            where (? is null or p.seniority = ?)
              and (? is null or p.work_mode = ?)
            group by all
            having ? is null or list_contains(list(lower(s.skill)), lower(?))
            order by p.first_seen desc, p.posting_id
            limit ? offset ?
            """,
            seniority,
            seniority,
            work_mode,
            work_mode,
            wanted,
            wanted,
            limit,
            offset,
        )

    return app
