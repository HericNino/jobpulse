import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jobpulse import store
from jobpulse.api import create_app
from jobpulse.pipeline import merge
from jobpulse.sources import arbeitnow, remotive

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    data = tmp_path_factory.mktemp("data")
    postings = {}
    raws = [
        *arbeitnow.parse(json.loads((FIXTURES / "arbeitnow.json").read_text())),
        *remotive.parse(json.loads((FIXTURES / "remotive.json").read_text())),
    ]
    merge(postings, raws, "2026-10-08")
    store.save(data / "postings.jsonl", postings)
    warehouse = data / "warehouse.duckdb"
    # built in a separate process, like in production: the API then opens the file read-only
    subprocess.run(
        [sys.executable, "-m", "jobpulse.cli", "warehouse", "--data", str(data), "--out", str(warehouse)],
        check=True,
        capture_output=True,
    )
    with TestClient(create_app(warehouse)) as c:
        yield c


def test_health(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "as_of": "2026-10-08", "active_postings": 4}


def test_skills_and_category_filter(client):
    skills = client.get("/skills", params={"limit": 3}).json()
    assert len(skills) == 3
    assert skills == sorted(skills, key=lambda s: (-s["postings"], s["skill"]))
    frontend = client.get("/skills", params={"category": "frontend"}).json()
    assert {s["skill"] for s in frontend} == {"React", "CSS"}


def test_skill_detail_accepts_aliases(client):
    body = client.get("/skills/postgres").json()
    assert body["skill"] == "PostgreSQL"
    assert body["postings"] == 2
    # pairs need at least two shared postings: only AWS appears with PostgreSQL in both
    assert body["companions"] == [{"skill": "AWS", "postings": 2, "share": 1.0}]


def test_unknown_skill_is_404(client):
    response = client.get("/skills/cobol")
    assert response.status_code == 404


def test_postings_filters(client):
    python = client.get("/postings", params={"skill": "python"}).json()
    assert python and all("Python" in p["skills"] for p in python)
    senior = client.get("/postings", params={"seniority": "senior"}).json()
    assert [p["title"] for p in senior] == ["Senior Python Developer (m/w/d)"]
    assert senior[0]["url"].startswith("https://")
    assert client.get("/postings", params={"limit": 1, "offset": 1}).json()[0]["id"] != client.get("/postings").json()[0]["id"]


def test_invalid_filter_is_rejected(client):
    assert client.get("/postings", params={"seniority": "wizard"}).status_code == 422
    assert client.get("/skills", params={"limit": 1000}).status_code == 422


def test_openapi_docs_are_served(client):
    assert client.get("/openapi.json").json()["info"]["title"] == "jobpulse"


def test_missing_warehouse_fails_at_startup(tmp_path):
    with pytest.raises(RuntimeError, match="warehouse not found"), TestClient(create_app(tmp_path / "nope.duckdb")):
        pass
