"""Checks on the evaluation itself: a perfect analyzer must score 100%, an empty one must fail,
and errors must never be scored as answers."""

import json
from pathlib import Path

from jobpulse import evals
from jobpulse.extract import Analysis
from jobpulse.skills import SKILLS

CASES = evals.load_cases(Path(__file__).parents[1] / "evals" / "cases.jsonl")
BY_TITLE = {c["posting"]["title"]: c for c in CASES}


def oracle(raw):
    e = BY_TITLE[raw.title]["expected"]
    s = e["salary"] or {}
    return (
        Analysis(
            skills=e["skills_required"],
            seniority=e["seniority"],
            remote=e["work_mode"],
            salary_min=s.get("min"),
            salary_max=s.get("max"),
            salary_currency=s.get("currency"),
            salary_period=s.get("period"),
        ),
        None,
    )


def null(raw):
    return Analysis(skills=[], seniority="unknown", remote="unknown"), None


def test_cases_are_well_formed():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids)) >= 30
    for c in CASES:
        e = c["expected"]
        assert set(e["skills_required"]) | set(e["skills_allowed"]) <= set(SKILLS), c["id"]
        assert not set(e["skills_required"]) & set(e["skills_allowed"]), c["id"]


def test_oracle_scores_perfectly(tmp_path):
    summary = evals.run(CASES, oracle, tmp_path / "oracle")
    for metric in ("skills_recall", "skills_precision", "seniority", "work_mode", "salary"):
        assert summary["metrics"][metric]["mean"] == 1.0, metric
    assert summary["errors"] == 0


def test_null_baseline_fails(tmp_path):
    summary = evals.run(CASES, null, tmp_path / "null")
    assert summary["metrics"]["skills_recall"]["mean"] == 0.0
    assert summary["metrics"]["seniority"]["mean"] < 0.4
    assert summary["metrics"]["work_mode"]["mean"] == 0.0
    # cases without a stated salary are right to leave it empty, so this is the share of such cases
    assert summary["metrics"]["salary"]["mean"] == sum(c["expected"]["salary"] is None for c in CASES) / len(CASES)


def test_errors_go_to_the_sidecar_and_runs_resume(tmp_path):
    calls = []

    def flaky(raw):
        calls.append(raw.title)
        if raw.title == CASES[0]["posting"]["title"]:
            raise ValueError("boom")
        return oracle(raw)

    out = tmp_path / "flaky"
    first = evals.run(CASES[:3], flaky, out)
    assert first["rows"] == 2 and first["errors"] == 1
    errors = [json.loads(line) for line in (out / "errors.jsonl").read_text().splitlines()]
    assert errors[0]["class"] == "harness_error" and errors[0]["prompt_id"] == CASES[0]["id"]

    calls.clear()
    evals.run(CASES[:3], flaky, out)  # resume: only the failed case is attempted again
    assert calls == [CASES[0]["posting"]["title"]]


def test_grade_salary_and_skills():
    expected = {
        "skills_required": ["Python", "SQL"],
        "skills_allowed": ["Docker"],
        "seniority": "mid",
        "work_mode": "remote",
        "salary": {"min": 50000, "max": 50000, "currency": "EUR", "period": "year"},
    }
    got = Analysis(
        skills=["Python", "Docker", "Kafka", "Prometheus"],  # Prometheus is outside the vocabulary: not scored
        seniority="mid",
        remote="hybrid",
        salary_min=50000,
        salary_currency="eur",
        salary_period="year",
    )
    g = evals.grade(expected, got)
    assert g["skills_recall"] == 0.5
    assert g["skills_precision"] == 2 / 3  # Kafka is neither required nor allowed
    assert (g["seniority"], g["work_mode"], g["salary"]) == (1.0, 0.0, 1.0)  # a single figure counts as min = max
    assert evals.grade(expected, None, refused=True)["refused"] == 1.0
