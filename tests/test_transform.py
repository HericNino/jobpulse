import csv
import json
from pathlib import Path

import pytest

from jobpulse import report
from jobpulse.skills import SKILLS

SEED = Path(__file__).parents[1] / "transform" / "seeds" / "skill_categories.csv"


def test_category_seed_matches_skill_vocabulary():
    with SEED.open() as f:
        seed = {row["skill"]: row["category"] for row in csv.DictReader(f)}
    expected = {name: category for name, (category, _) in SKILLS.items()}
    assert seed == expected, "regenerate transform/seeds/skill_categories.csv from skills.py"


def test_bad_data_stops_the_report(tmp_path):
    """dbt data tests guard the dashboard: an unexpected value fails the build instead of being published."""
    bad = {
        "id": "x:1",
        "source": "x",
        "url": "",
        "title": "Engineer",
        "company": "Co",
        "location": "",
        "country": None,
        "posted_at": "2026-10-01",
        "first_seen": "2026-10-01",
        "last_seen": "2026-10-01",
        "remote": "sometimes",  # not an accepted work mode
        "seniority": "senior",
        "skills": ["Python"],
        "analyzed_by": "keywords",
    }
    path = tmp_path / "postings.jsonl"
    path.write_text(json.dumps(bad) + "\n")
    with pytest.raises(report.DbtError):
        report.build(path)
