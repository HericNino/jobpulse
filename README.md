# jobpulse

Which skills are tech job postings asking for, and how is that changing? jobpulse collects postings from public job board APIs once a day, pulls out the facts (skills, seniority, remote or not, pay), and publishes a small dashboard.

I built it while job hunting, to answer questions like "is it worth learning Kubernetes next?" with numbers instead of gut feeling.

## How it works

```
GitHub Actions, daily
  └─ jobpulse run
       ├─ fetch      Arbeitnow and Remotive public APIs
       ├─ filter     tech roles only (title or at least three concrete skills)
       ├─ analyze    new postings only: keyword rules, or Claude if a key is set
       ├─ store      data/postings.jsonl (committed, one line per posting)
       └─ report     dbt build on DuckDB (models + data tests) → data/report.json
  └─ publish site/ + report.json to GitHub Pages
```

- **No server, no database to host.** The data lives in the repository as JSON Lines, sorted, so each day's commit is a readable diff of what changed.
- **Transformations in dbt.** `transform/` is a dbt project that reads the JSON Lines file with DuckDB: staging models type and clean it, marts compute the dashboard's numbers (top skills, weekly trends, skill pairs, pay quartiles). 18 data tests (uniqueness, accepted values, relationships, ranges) run on every build, and a failing test stops the report instead of publishing bad numbers.
- **Facts, not copies.** Posting descriptions are read once in memory and never stored. The repo keeps title, company, link, dates and the extracted fields; the original stays on its job board.
- **Two analyzers, one vocabulary.** A keyword matcher (`src/jobpulse/skills.py`) handles aliases ("Postgres" → PostgreSQL) and awkward names (C++, .NET, Node.js) without mistaking "Java" in "JavaScript". With `ANTHROPIC_API_KEY` set, new postings are analyzed by Claude instead, using structured output, which also catches seniority, work mode and stated salaries. The number of model calls per run is capped, and after repeated failures it falls back to keywords for the rest of the run.
- **Polite collection.** One run a day, a descriptive User-Agent, and only sources that publish an API for this purpose.

## Running locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run jobpulse run                      # fetch, analyze, write data/
uv run jobpulse run --max-model-calls 0  # keywords only, no API key needed
uv run jobpulse report                   # rebuild data/report.json from stored postings

uv run pytest
uv run ruff check . && uv run ruff format --check .
```

Working on the SQL directly:

```bash
cd transform
uv run dbt build --profiles-dir . --vars "{postings_path: '$PWD/../data/postings.jsonl'}"
uv run dbt docs generate --profiles-dir . && uv run dbt docs serve --profiles-dir .   # lineage graph
```

To look at the dashboard, serve `site/` with `data/report.json` next to it:

```bash
mkdir -p _site/data && cp site/* _site/ && cp data/report.json _site/data/
python -m http.server -d _site
```

## Setting up the daily run

1. **Settings → Pages → Source:** GitHub Actions.
2. Optional: add an `ANTHROPIC_API_KEY` repository secret (Settings → Secrets and variables → Actions) for model-based analysis. Without it everything still works with keyword rules.
3. Run **Actions → Collect and publish → Run workflow** once, or wait for the next scheduled run.

## Layout

```
src/jobpulse/
  sources/      one module per job board: parse() is pure and tested, fetch() does the HTTP
  skills.py     skill vocabulary, aliases, keyword matcher, seniority and remote rules
  extract.py    keyword analysis and the Claude analyzer
  pipeline.py   merging new and known postings, pruning non-tech ones
  store.py      JSONL storage
  report.py     runs dbt and shapes the marts into report.json
  cli.py
transform/
  models/staging/   typed views over data/postings.jsonl
  models/marts/     the tables behind the dashboard
  seeds/            skill categories (generated from skills.py; a test keeps them in sync)
  tests/            singular and generic data tests
site/           static dashboard (HTML, CSS, vanilla JS, no build step)
tests/          pytest, with saved API responses as fixtures
```

## Ideas

- Croatian job boards, once I've checked their terms
- Salary normalization across currencies
- Incremental dbt models once the history grows
- Per-country views
- An API (FastAPI) on top of the same marts
- Use the Message Batches API for model analysis, which halves the cost

## License

MIT
