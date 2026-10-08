from types import SimpleNamespace

from jobpulse.extract import ClaudeAnalyzer, Extraction, analyze_keywords
from jobpulse.models import RawPosting

RAW = RawPosting(
    source="test",
    source_id="1",
    url="https://example.com/1",
    title="Senior Data Engineer",
    company="Example",
    location="Zagreb, Croatia (hybrid)",
    posted_at="2026-10-01",
    description="Airflow, dbt and Postgres. Salary 45.000 - 60.000 EUR per year.",
    remote=False,
)


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


USAGE = SimpleNamespace(input_tokens=900, output_tokens=120, cache_read_input_tokens=None, cache_creation_input_tokens=None)


def fake_client(response):
    messages = FakeMessages(response)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def test_keyword_analysis():
    analysis = analyze_keywords(RAW)
    assert analysis.skills == ["Airflow", "PostgreSQL", "dbt"]
    assert analysis.seniority == "senior"
    assert analysis.remote == "hybrid"
    assert analysis.salary_min is None


def test_claude_analysis_normalizes_output():
    output = Extraction(
        skills=["airflow", "Postgres", "dbt", "Data modeling", " "],
        seniority="senior",
        work_mode="hybrid",
        country="hr",
        salary_min=45000,
        salary_max=60000,
        salary_currency="eur",
        salary_period="year",
    )
    client, messages = fake_client(SimpleNamespace(stop_reason="end_turn", parsed_output=output, model="claude-opus-5-5", usage=USAGE))
    analysis = ClaudeAnalyzer(client=client, model="claude-opus-5-5").analyze(RAW)

    assert analysis.skills == ["Airflow", "Data modeling", "PostgreSQL", "dbt"]
    assert analysis.country == "HR"
    assert analysis.salary_currency == "EUR"
    assert (analysis.salary_min, analysis.salary_max, analysis.salary_period) == (45000, 60000, "year")
    assert analysis.analyzed_by == "claude-opus-5-5"

    call = messages.calls[0]
    assert call["output_format"] is Extraction
    assert call["fallbacks"] == "default"
    assert "<posting>" in call["messages"][0]["content"]
    assert "PostgreSQL" in call["system"]  # the canonical vocabulary is in the prompt


def test_claude_refusal_returns_none():
    client, _ = fake_client(SimpleNamespace(stop_reason="refusal", parsed_output=None, model="claude-opus-5-5", usage=USAGE))
    assert ClaudeAnalyzer(client=client).analyze(RAW) is None


def test_detailed_call_records_usage_and_output():
    output = Extraction(
        skills=["Python"],
        seniority="mid",
        work_mode="remote",
        country=None,
        salary_min=None,
        salary_max=None,
        salary_currency=None,
        salary_period=None,
    )
    client, _ = fake_client(SimpleNamespace(stop_reason="end_turn", parsed_output=output, model="claude-opus-5-5", usage=USAGE))
    analysis, call = ClaudeAnalyzer(client=client, model="claude-opus-5-5").analyze_detailed(RAW)
    assert analysis.skills == ["Python"]
    assert call.usage == {"input_tokens": 900, "output_tokens": 120, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    assert call.output["work_mode"] == "remote"
    assert call.model == "claude-opus-5-5" and call.stop_reason == "end_turn"
