import json
from pathlib import Path

from jobpulse import report, store
from jobpulse.extract import Analysis
from jobpulse.models import RawPosting
from jobpulse.pipeline import dedupe, merge, prune
from jobpulse.sources import arbeitnow, remotive

FIXTURES = Path(__file__).parent / "fixtures"


def fetched() -> list[RawPosting]:
    return [
        *arbeitnow.parse(json.loads((FIXTURES / "arbeitnow.json").read_text())),
        *remotive.parse(json.loads((FIXTURES / "remotive.json").read_text())),
    ]


def test_merge_adds_new_and_refreshes_known():
    postings = {}
    stats = merge(postings, fetched(), "2026-10-06")
    assert (stats.seen, stats.new) == (4, 4)
    python_job = postings["arbeitnow:senior-python-developer-acme-berlin-123"]
    assert python_job.skills == ["AWS", "Docker", "FastAPI", "Kubernetes", "PostgreSQL", "Python"]
    assert python_job.seniority == "senior"
    assert python_job.analyzed_by == "keywords"

    stats = merge(postings, fetched()[:1], "2026-10-08")
    assert (stats.seen, stats.new) == (1, 0)
    assert python_job.first_seen == "2026-10-06"
    assert python_job.last_seen == "2026-10-08"


def test_model_budget_and_fallback():
    calls = []

    def analyze(raw):
        calls.append(raw.id)
        if raw.source == "remotive":
            raise RuntimeError("API down")
        return Analysis(skills=["Python"], seniority="mid", remote="onsite", analyzed_by="test-model")

    postings = {}
    stats = merge(postings, fetched(), "2026-10-06", analyze=analyze, max_model_calls=1)
    # first call succeeds and uses the budget; the rest fall back to keywords without calling
    assert calls == ["arbeitnow:senior-python-developer-acme-berlin-123"]
    assert stats.analyzed_by_model == 1
    assert postings[calls[0]].analyzed_by == "test-model"
    assert postings["remotive:1912345"].analyzed_by == "keywords"

    # failures don't consume budget and don't stop the run
    calls.clear()
    postings = {}
    stats = merge(postings, list(reversed(fetched())), "2026-10-06", analyze=analyze, max_model_calls=1)
    assert len(calls) == 3 and stats.analyzed_by_model == 1 and stats.new == 4


def test_dedupe_keeps_first():
    raws = fetched()
    assert len(dedupe(raws + raws)) == 4


def test_jsonl_round_trip_is_sorted_and_stable(tmp_path):
    postings = {}
    merge(postings, fetched(), "2026-10-06")
    path = tmp_path / "postings.jsonl"
    store.save(path, postings)
    first = path.read_text()
    assert [json.loads(line)["id"] for line in first.splitlines()] == sorted(postings)
    store.save(path, store.load(path))
    assert path.read_text() == first
    assert "description" not in first  # we never store posting texts


def test_report_aggregates():
    postings = {}
    merge(postings, fetched(), "2026-09-20")  # all four first seen three weeks ago
    merge(postings, fetched()[:2], "2026-10-08")  # only the arbeitnow two are still listed

    result = report.build(store.to_sqlite(postings.values()))
    assert result["as_of"] == "2026-10-08"
    assert result["summary"]["active"] == 2
    assert result["summary"]["all_time"] == 4
    assert result["summary"]["new_this_week"] == 0
    top = {row["skill"]: row for row in result["top_skills"]}
    assert top["Python"]["postings"] == 1 and top["Python"]["share"] == 0.5
    assert top["React"]["category"] == "Frontend"
    assert "Kafka" not in top  # remotive postings are no longer active
    assert result["trend"]["weeks"] == [{"week": "2026-09-14", "total": 4}]
    assert {(r["key"], r["postings"]) for r in result["seniority"]} == {("senior", 1), ("junior", 1)}


def test_salary_quartiles_need_three_postings():
    postings = {}
    raws = fetched()
    for i, raw in enumerate(raws):
        merge(
            postings,
            [raw],
            "2026-10-08",
            analyze=lambda r, i=i: Analysis(
                skills=["Python"],
                seniority="mid",
                remote="remote",
                salary_min=60_000 + i * 10_000,
                salary_max=80_000 + i * 10_000,
                salary_currency="EUR",
                salary_period="year",
                analyzed_by="test",
            ),
            max_model_calls=1,
        )
    salaries = report.build(store.to_sqlite(postings.values()))["salaries"]
    assert salaries["EUR"]["postings"] == 4
    assert salaries["EUR"]["median"] == 85_000
    assert salaries["EUR"]["by_skill"] == [{"skill": "Python", "postings": 4, "median": 85_000}]


def test_empty_report():
    assert report.build(store.to_sqlite([]))["summary"] == {"active": 0}


def test_model_is_dropped_after_repeated_failures():
    calls = []

    def broken(raw):
        calls.append(raw.id)
        raise RuntimeError("401 invalid key")

    many = [RawPosting("t", str(i), "", f"Python Developer {i}", "Co", "", "2026-10-01", "Python") for i in range(10)]
    postings = {}
    stats = merge(postings, many, "2026-10-06", analyze=broken, max_model_calls=100)
    assert len(calls) == 3
    assert stats.new == 10 and stats.analyzed_by_model == 0


def test_trend_leaves_out_the_unfinished_week():
    postings = {}
    merge(postings, fetched()[:2], "2026-09-30")  # Wednesday, week of 28 Sep (finished by 8 Oct)
    merge(postings, fetched()[2:], "2026-10-08")  # Thursday, week of 5 Oct (still running)
    weeks = report.build(store.to_sqlite(postings.values()))["trend"]["weeks"]
    assert weeks == [{"week": "2026-09-28", "total": 2}]


def test_non_tech_postings_are_skipped_and_never_sent_to_the_model():
    calls = []
    sales = RawPosting("t", "s", "", "Account Executive, DACH", "Co", "", "2026-10-01", "Sell our SaaS. Salesforce, SQL a plus.")
    dev = RawPosting("t", "d", "", "Backend Engineer", "Co", "", "2026-10-01", "Go and PostgreSQL")
    postings = {}
    stats = merge(postings, [sales, dev], "2026-10-06", analyze=lambda r: calls.append(r.id), max_model_calls=10)
    assert list(postings) == ["t:d"]
    assert stats.skipped == 1
    assert calls == ["t:d"]


def test_prune_removes_stored_non_tech_postings():
    postings = {}
    merge(postings, fetched(), "2026-10-06")
    postings["arbeitnow:junior-frontend-engineer-beta-456"].title = "Account Manager"
    postings["arbeitnow:junior-frontend-engineer-beta-456"].skills = ["SQL"]
    assert prune(postings) == 1
    assert len(postings) == 3
