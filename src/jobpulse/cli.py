"""jobpulse command line.

jobpulse collect   fetch sources, analyze new postings, update data/postings.jsonl
jobpulse report    rebuild data/report.json from data/postings.jsonl
jobpulse run       both
jobpulse eval      run an analyzer over evals/cases.jsonl and grade it
jobpulse compare   paired comparison of two eval runs
jobpulse cases     write evals/CASES.md, a readable view of the eval cases
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

from . import report, store
from .pipeline import dedupe, merge, prune
from .sources import SOURCES, make_client

log = logging.getLogger("jobpulse")


def collect(data_dir: Path, sources: list[str], pages: int, max_model_calls: int) -> int:
    """Returns how many sources answered."""
    postings_path = data_dir / "postings.jsonl"
    postings = store.load(postings_path)

    fetched = []
    working = 0
    with make_client() as client:
        for name in sources:
            try:
                batch = SOURCES[name](client, pages)
                log.info("%s: %d postings", name, len(batch))
                fetched.extend(batch)
                working += 1
            except Exception as error:  # one broken source shouldn't stop the others
                log.error("%s failed: %s", name, error)

    analyzer = None
    if os.environ.get("ANTHROPIC_API_KEY") and max_model_calls > 0:
        from .extract import ClaudeAnalyzer

        analyzer = ClaudeAnalyzer().analyze
    else:
        log.info("keyword analysis only (pass --max-model-calls N with ANTHROPIC_API_KEY set to use Claude)")

    pruned = prune(postings)
    stats = merge(postings, dedupe(fetched), date.today().isoformat(), analyzer, max_model_calls)
    store.save(postings_path, postings)
    log.info(
        "seen %d, new %d (%d analyzed by model), skipped %d non-tech, pruned %d, total %d",
        stats.seen,
        stats.new,
        stats.analyzed_by_model,
        stats.skipped,
        pruned,
        len(postings),
    )
    return working


def write_report(data_dir: Path) -> None:
    postings_path = data_dir / "postings.jsonl"
    if not postings_path.exists():
        postings_path.touch()
    result = report.build(postings_path)
    (data_dir / "report.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    log.info("report: %s active postings as of %s", result["summary"]["active"], result["as_of"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jobpulse", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["collect", "report", "run", "eval", "compare", "cases"])
    parser.add_argument("paths", nargs="*", type=Path, help="compare: two eval run directories")
    parser.add_argument("--data", type=Path, default=Path("data"), help="data directory (default: data)")
    parser.add_argument("--sources", default=",".join(SOURCES), help=f"comma separated, from: {', '.join(SOURCES)}")
    parser.add_argument("--pages", type=int, default=3, help="pages per paginated source")
    parser.add_argument(
        "--max-model-calls",
        type=int,
        default=0,
        help="analyze up to this many new postings with Claude (needs ANTHROPIC_API_KEY; default 0 = keywords only)",
    )
    parser.add_argument("--variant", choices=["keywords", "claude"], default="keywords", help="eval: which analyzer")
    parser.add_argument("--model", help="eval: Claude model (default: JOBPULSE_MODEL or claude-opus-5-5)")
    parser.add_argument("--reps", type=int, default=1, help="eval: repetitions per case")
    parser.add_argument("--cases-file", type=Path, default=Path("evals/cases.jsonl"))
    parser.add_argument("--runs", type=Path, default=Path("evals/runs"), help="eval: where run directories go")
    args = parser.parse_args(argv)

    if args.command in ("eval", "compare", "cases"):
        return _evals(args, parser)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    unknown = [s for s in sources if s not in SOURCES]
    if unknown:
        parser.error(f"unknown source(s): {', '.join(unknown)}")

    exit_code = 0
    if args.command in ("collect", "run") and collect(args.data, sources, args.pages, args.max_model_calls) == 0:
        log.error("no source could be reached")
        exit_code = 1
    if args.command in ("report", "run"):
        write_report(args.data)
    return exit_code


def _evals(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    from . import evals

    if args.command == "cases":
        out = args.cases_file.with_name("CASES.md")
        out.write_text(evals.cases_markdown(evals.load_cases(args.cases_file)), encoding="utf-8")
        print(f"wrote {out}")
        return 0
    if args.command == "compare":
        if len(args.paths) != 2:
            parser.error("compare needs two run directories")
        print(evals.compare(*args.paths))
        return 0

    cases = evals.load_cases(args.cases_file)
    if args.variant == "keywords":
        analyze, model, name = evals.keywords_variant, None, "keywords"
    else:
        analyze, model = evals.claude_variant(args.model)
        name = model
    summary = evals.run(cases, analyze, args.runs / name, expected_model=model, reps=args.reps)
    print(evals.summary_markdown(summary, name))
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
