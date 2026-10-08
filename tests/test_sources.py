import json
from pathlib import Path

from jobpulse.sources import arbeitnow, remotive
from jobpulse.text import html_to_text, to_day

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_arbeitnow_parse_skips_broken_entries_and_cleans_html():
    postings = arbeitnow.parse(load("arbeitnow.json"))
    assert [p.id for p in postings] == [
        "arbeitnow:senior-python-developer-acme-berlin-123",
        "arbeitnow:junior-frontend-engineer-beta-456",
    ]
    first = postings[0]
    assert first.company == "Acme GmbH"
    assert first.remote is False
    assert first.posted_at == "2025-10-06"
    assert "<" not in first.description
    assert "Docker & Kubernetes" in first.description


def test_remotive_parse():
    postings = remotive.parse(load("remotive.json"))
    assert len(postings) == 2
    staff = postings[0]
    assert staff.id == "remotive:1912345"
    assert staff.remote is True
    assert staff.salary_text == "$150k - $190k"
    assert staff.posted_at == "2026-10-05"
    assert postings[1].salary_text is None


def test_html_to_text_keeps_paragraph_breaks():
    assert html_to_text("<p>One</p><p>Two&nbsp;words</p>") == "One\n\nTwo words"


def test_to_day_accepts_timestamps_and_iso_strings():
    assert to_day(0) == "1970-01-01"
    assert to_day("2026-10-05T23:59:00Z") == "2026-10-05"
