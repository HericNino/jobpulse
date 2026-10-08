# jobpulse

Which skills are tech job postings asking for, and how is that changing? jobpulse collects postings from public job board APIs once a day, pulls out the facts (skills, seniority, remote or not, pay), and publishes a small dashboard.

I built it while job hunting, to answer questions like "is it worth learning Kubernetes next?" with numbers instead of gut feeling.

## How it works

```
GitHub Actions, daily
  └─ jobpulse run
       ├─ fetch      Arbeitnow and Remotive public APIs
       ├─ filter     tech roles only (title or at least three concrete skills)
       ├─ analyze    new postings only, with keyword rules (Claude only when run by hand)
       ├─ store      data/postings.jsonl (committed, one line per posting)
       └─ report     dbt build on DuckDB (models + data tests) → data/report.json
  └─ publish site/ + report.json to GitHub Pages
```

- **No server, no database to host.** The data lives in the repository as JSON Lines, sorted, so each day's commit is a readable diff of what changed.
- **Transformations in dbt.** `transform/` is a dbt project that reads the JSON Lines file with DuckDB: staging models type and clean it, marts compute the dashboard's numbers (top skills, weekly trends, skill pairs, pay quartiles). 18 data tests (uniqueness, accepted values, relationships, ranges) run on every build, and a failing test stops the report instead of publishing bad numbers.
- **Facts, not copies.** Posting descriptions are read once in memory and never stored. The repo keeps title, company, link, dates and the extracted fields; the original stays on its job board.
- **Two analyzers, one vocabulary.** A keyword matcher (`src/jobpulse/skills.py`) handles aliases ("Postgres" → PostgreSQL) and awkward names (C++, .NET, Node.js) without mistaking "Java" in "JavaScript". Claude can analyze new postings instead, using structured output, which also catches seniority, work mode and stated salaries. That only happens when asked for explicitly (`--max-model-calls N` with `ANTHROPIC_API_KEY` set); the scheduled run never uses it, so nothing automated spends API credit. Calls are capped per run, and after repeated failures it falls back to keywords.
- **Polite collection.** One run a day, a descriptive User-Agent, and only sources that publish an API for this purpose.

## Running locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras
uv run jobpulse run                       # fetch, analyze with keywords, write data/
uv run jobpulse run --max-model-calls 50  # also let Claude analyze up to 50 new postings (needs ANTHROPIC_API_KEY)
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

## Evaluation

How good is each analyzer? `evals/cases.jsonl` holds 30 hand-written postings with expected answers, chosen to cover the cases that broke things on real data or are easy to get wrong: German, French and Croatian postings, "Java" next to "JavaScript", "you'll go on-call", "React Native", salaries per hour, per month and as "90-110k", "competitive salary" with no figure, equity instead of pay, and non-tech roles. `evals/CASES.md` shows them in readable form.

Grading is programmatic: recall and precision on skills (only the shared vocabulary is scored), and exact match on seniority, work mode and salary. Each run writes per-case results, full transcripts and an errors file, and reports 95% intervals over cases. Refusals and API errors are counted separately and never scored as wrong answers.

```bash
uv run jobpulse eval --variant keywords             # free, runs anywhere
uv run jobpulse eval --variant claude --reps 2      # needs ANTHROPIC_API_KEY
uv run jobpulse compare evals/runs/keywords evals/runs/claude-opus-5-5
```

The Claude run also exists as a GitHub Action (**Actions → Evaluate analyzers → Run workflow**) that only runs when started by hand. It reads the key from the `ANTHROPIC_API_KEY` repository secret and puts the comparison in the run summary.

### Improving the keyword analyzer against the eval

The first keyword baseline missed Croatian word endings ("Reactu", "TypeScriptom"), experience stated in years, work mode mentioned only in the description, and every salary. Before changing anything, I wrote 10 more cases (`evals/holdout.jsonl`) and set them aside, then improved the rules using only the main 30: a salary parser (`src/jobpulse/salary.py`), experience-based seniority, multilingual work-mode phrases, inflected and hyphenated skill names, and context rules for ambiguous names like Go and Rust. The held-out set was scored once, at the end:

| Held-out cases (10) | Before | After |
|---|---|---|
| Skill recall | 76% | 93% |
| Skill precision | 100% | 100% |
| Seniority | 50% | 100% |
| Work mode | 80% | 100% |
| Salary | 20% | 100% |

With ten cases the intervals are wide (±10 to ±33 points), so this shows the rules generalize rather than measuring them precisely. The two remaining misses are left in on purpose: "PySpark" isn't read as Python, and "learn Go" isn't read as the language. The main set now scores 100% on everything, which says little since it was used for tuning. New postings get the improved analysis; stored ones keep what they had, because descriptions aren't kept.

## API

A small read-only HTTP API serves the same numbers (FastAPI, interactive docs at `/docs`):

| Endpoint | What it returns |
|---|---|
| `GET /health` | status, data date, number of active postings |
| `GET /summary` | the headline numbers |
| `GET /skills?limit=&category=` | skills by demand, with how many companies ask for each |
| `GET /skills/{name}` | one skill (aliases work: `/skills/k8s`): what it's paired with, weekly trend, median pay |
| `GET /companies?limit=` | companies with the most open postings |
| `GET /postings?skill=&seniority=&work_mode=&limit=&offset=` | active postings with links to the originals |

It reads a DuckDB file built from the dbt models and opens it read-only, so it never touches the source data or the network.

```bash
uv sync --all-extras
uv run jobpulse warehouse                                   # builds .dbt/warehouse.duckdb
uv run uvicorn jobpulse.api:create_app --factory --reload   # http://localhost:8000/docs
```

### Docker

```bash
docker compose up --build      # http://localhost:8000/docs
```

The image is built in two stages. The first installs the pipeline dependencies and builds the warehouse from `data/postings.jsonl`; the second keeps only a separate environment with what the API imports, plus the warehouse file. That takes it from 748 MB (one environment with dbt and the Anthropic SDK) to 321 MB. It runs as a non-root user, works with a read-only filesystem, and has a health check.

The **Image** workflow builds it, starts the container and checks the endpoints, then publishes it to GitHub Container Registry (`ghcr.io/hericnino/jobpulse`, tagged `latest`, the commit and the date). It also runs after each daily collection, so the published image always has the latest data.

## Setting up the daily run

1. **Settings → Pages → Source:** GitHub Actions.
2. Run **Actions → Collect and publish → Run workflow** once, or wait for the next scheduled run.

The daily run uses keyword rules only. An `ANTHROPIC_API_KEY` repository secret is used by one workflow, **Evaluate analyzers**, which runs only when started by hand.

## Layout

```
src/jobpulse/
  sources/      one module per job board: parse() is pure and tested, fetch() does the HTTP
  skills.py     skill vocabulary, aliases, keyword matcher, seniority and remote rules
  extract.py    keyword analysis and the Claude analyzer
  pipeline.py   merging new and known postings, pruning non-tech ones
  store.py      JSONL storage
  report.py     runs dbt and shapes the marts into report.json
  evals.py      grading and running the analyzer evaluation
  salary.py     finding stated pay in posting text
  api.py        the read-only HTTP API
  cli.py
transform/
  models/staging/   typed views over data/postings.jsonl
  models/marts/     the tables behind the dashboard
  seeds/            skill categories (generated from skills.py; a test keeps them in sync)
  tests/            singular and generic data tests
evals/          evaluation cases and run results
site/           static dashboard (HTML, CSS, vanilla JS, no build step)
tests/          pytest, with saved API responses as fixtures
```

## Ideas

- Croatian job boards, once I've checked their terms
- Salary normalization across currencies
- Incremental dbt models once the history grows
- Per-country views
- Deploy the API image to a cloud host with Terraform
- Use the Message Batches API for model analysis, which halves the cost

## License

MIT
