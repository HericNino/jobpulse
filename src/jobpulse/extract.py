"""Turning a raw posting into structured facts.

`analyze_keywords` is free and deterministic. `ClaudeAnalyzer` reads the full
description and also picks up salary, seniority and work mode that keyword
rules miss. It's used when ANTHROPIC_API_KEY is set, for new postings only.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

from .models import RawPosting, Remote, Seniority
from .salary import parse_salary
from .skills import SKILLS, canonical, guess_remote, guess_seniority, match_skills

DEFAULT_MODEL = "claude-opus-5-5"


@dataclass
class Analysis:
    skills: list[str]
    seniority: Seniority
    remote: Remote
    country: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    salary_period: Literal["year", "month", "hour"] | None = None
    analyzed_by: str = "keywords"


def analyze_keywords(raw: RawPosting) -> Analysis:
    salary = parse_salary(raw.salary_text) or parse_salary(raw.description)
    return Analysis(
        skills=match_skills(f"{raw.title}\n{raw.description}", raw.tags),
        seniority=guess_seniority(raw.title, raw.description),
        remote=guess_remote(raw.remote, raw.title, raw.location, raw.description),
        salary_min=salary.min if salary else None,
        salary_max=salary.max if salary else None,
        salary_currency=salary.currency if salary else None,
        salary_period=salary.period if salary else None,
    )


class Extraction(BaseModel):
    """Schema Claude fills in for each posting."""

    skills: list[str] = Field(description="Technical skills the role requires or clearly uses, as canonical names from the list")
    seniority: Seniority
    work_mode: Remote
    country: str | None = Field(description="ISO 3166-1 alpha-2 code of the job's country, or null if fully remote/unclear")
    salary_min: int | None = Field(description="Lower bound of the stated pay, as a plain number")
    salary_max: int | None = Field(description="Upper bound of the stated pay, as a plain number")
    salary_currency: str | None = Field(description="ISO 4217 code such as EUR or USD")
    salary_period: Literal["year", "month", "hour"] | None


SYSTEM = f"""You extract facts from job postings for a labour-market report.

Use only what the posting says. Leave salary fields null unless an amount is stated; never estimate one.
For skills, list the technologies and practices the role actually involves, using these canonical names when one applies:
{", ".join(SKILLS)}
Only add a name outside that list for a clearly technical skill that is central to the role.
Seniority: infer from title and stated experience (intern, junior <2y, mid 2-5y, senior 5y+,
lead for leads/principals/staff). Use unknown if there are no clues.
work_mode: remote, hybrid, onsite, or unknown."""


class ClaudeAnalyzer:
    def __init__(self, client: anthropic.Anthropic | None = None, model: str | None = None) -> None:
        self.client = client or anthropic.Anthropic()
        self.model = model or os.environ.get("JOBPULSE_MODEL", DEFAULT_MODEL)

    def analyze(self, raw: RawPosting) -> Analysis | None:
        """Returns None when the model declines, so the caller can fall back to keywords."""
        return self.analyze_detailed(raw)[0]

    def analyze_detailed(self, raw: RawPosting) -> tuple[Analysis | None, Call]:
        """Like analyze(), plus what the evaluation needs: prompt, raw output, model, usage."""
        prompt = build_prompt(raw)
        started = time.monotonic()
        response = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_format=Extraction,
            # a routine extraction task: keep thinking short
            output_config={"effort": "low"},
            # retry server-side on another model if a safety classifier declines
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        out = response.parsed_output
        usage = response.usage
        call = Call(
            prompt=prompt,
            output=out.model_dump() if out is not None else None,
            model=response.model,
            stop_reason=response.stop_reason,
            latency_s=round(time.monotonic() - started, 2),
            usage={
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read_input_tokens": usage.cache_read_input_tokens or 0,
                "cache_creation_input_tokens": usage.cache_creation_input_tokens or 0,
            },
        )
        if response.stop_reason == "refusal" or out is None:
            return None, call
        skills = sorted({canonical(s) or s.strip() for s in out.skills if s.strip()})
        analysis = Analysis(
            skills=skills,
            seniority=out.seniority,
            remote=out.work_mode,
            country=out.country.upper() if out.country else None,
            salary_min=out.salary_min,
            salary_max=out.salary_max,
            salary_currency=out.salary_currency.upper() if out.salary_currency else None,
            salary_period=out.salary_period,
            analyzed_by=response.model,
        )
        return analysis, call


def build_prompt(raw: RawPosting) -> str:
    return (
        f"<posting>\nTitle: {raw.title}\nCompany: {raw.company}\nLocation: {raw.location}\n"
        f"Tags: {', '.join(raw.tags)}\nSalary field: {raw.salary_text or 'none'}\n\n{raw.description}\n</posting>"
    )


@dataclass
class Call:
    prompt: str
    output: dict | None
    model: str
    stop_reason: str | None
    latency_s: float
    usage: dict
