"""Evaluation of the posting analyzers against hand-labelled cases (evals/cases.jsonl).

Each case is a posting plus the expected answer. An analyzer variant
(`keywords` or `claude`) is run over every case, and each output is graded
programmatically:

    skills_recall     required skills found / required skills
    skills_precision  predicted skills that are required or allowed / predicted skills
    seniority         1 if exactly right
    work_mode         1 if exactly right
    salary            1 if min, max, currency and period all match (or both are empty)
    refused           1 if the model declined (other metrics are then left out)

Only skills from the shared vocabulary are scored; anything else the model
names is counted separately as `off_vocabulary`.

A run writes, per variant directory:
    results.jsonl          one row per (case, rep), written as each case finishes
    traces/<id>_rep<k>.json  the full exchange for that case
    errors.jsonl           attempts that produced nothing gradable (API errors, timeouts, wrong model)
    summary.json / summary.md
Re-running into the same directory resumes: finished (case, rep) pairs are skipped.
"""

from __future__ import annotations

import json
import math
import random
import statistics
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from .extract import SYSTEM, Analysis, Call, analyze_keywords, build_prompt
from .models import RawPosting
from .skills import SKILLS

METRICS = ["skills_recall", "skills_precision", "seniority", "work_mode", "salary", "refused"]
LABELS = {
    "skills_recall": "Skill recall",
    "skills_precision": "Skill precision",
    "seniority": "Seniority",
    "work_mode": "Work mode",
    "salary": "Salary",
    "refused": "Refused",
}
# USD per million tokens (input, output); cache reads at 0.1x and writes at 1.25x input
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0)}

Analyzer = Callable[[RawPosting], tuple[Analysis | None, Call | None]]


# ---------- cases ----------


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def to_raw(case: dict) -> RawPosting:
    p = case["posting"]
    return RawPosting(
        source="eval",
        source_id=case["id"],
        url="",
        title=p["title"],
        company=p["company"],
        location=p["location"],
        posted_at="2026-01-01",
        description=p["description"],
        remote=p.get("remote"),
        tags=tuple(p.get("tags") or ()),
        salary_text=p.get("salary_text"),
    )


# ---------- grading ----------


def _salary(min_: int | None, max_: int | None, currency: str | None, period: str | None) -> tuple | None:
    if min_ is None and max_ is None:
        return None
    low, high = min_ if min_ is not None else max_, max_ if max_ is not None else min_
    return (int(low), int(high), (currency or "").upper(), period)


def grade(expected: dict, analysis: Analysis | None, refused: bool = False) -> dict:
    if refused or analysis is None:
        return {m: None for m in METRICS} | {"refused": 1.0 if refused else None}

    required = set(expected["skills_required"])
    acceptable = required | set(expected["skills_allowed"])
    predicted = {s for s in analysis.skills if s in SKILLS}

    want = expected["salary"]
    want_salary = _salary(want["min"], want["max"], want["currency"], want["period"]) if want else None
    got_salary = _salary(analysis.salary_min, analysis.salary_max, analysis.salary_currency, analysis.salary_period)

    return {
        "skills_recall": len(predicted & required) / len(required) if required else None,
        "skills_precision": len(predicted & acceptable) / len(predicted) if predicted else None,
        "seniority": float(analysis.seniority == expected["seniority"]),
        "work_mode": float(analysis.remote == expected["work_mode"]),
        "salary": float(want_salary == got_salary),
        "refused": 0.0,
    }


# ---------- analyzers ----------


def keywords_variant(raw: RawPosting) -> tuple[Analysis, None]:
    return analyze_keywords(raw), None


def claude_variant(model: str | None = None) -> tuple[Analyzer, str]:
    import anthropic

    from .extract import ClaudeAnalyzer

    # retries are handled below so they can be counted
    analyzer = ClaudeAnalyzer(client=anthropic.Anthropic(max_retries=0, timeout=180), model=model)
    return analyzer.analyze_detailed, analyzer.model


def _retryable(error: Exception) -> bool:
    import anthropic

    return isinstance(
        error,
        anthropic.RateLimitError | anthropic.InternalServerError | anthropic.APIConnectionError | anthropic.APITimeoutError,
    ) or getattr(error, "status_code", None) in (429, 529)


# ---------- running ----------


def run(
    cases: list[dict],
    analyze: Analyzer,
    out_dir: Path,
    *,
    expected_model: str | None = None,
    reps: int = 1,
    workers: int = 4,
    max_attempts: int = 4,
    case_timeout: float = 300,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "traces").mkdir(exist_ok=True)
    results_path, errors_path = out_dir / "results.jsonl", out_dir / "errors.jsonl"
    done = {(r["prompt_id"], r["rep"]) for r in _read_jsonl(results_path)}
    todo = [(case, rep) for case in cases for rep in range(reps) if (case["id"], rep) not in done]
    lock = threading.Lock()

    def append(path: Path, row: dict) -> None:
        with lock, path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def attempt(case: dict, rep: int) -> None:
        raw = to_raw(case)
        started = time.monotonic()
        for n in range(1, max_attempts + 1):
            try:
                analysis, call = analyze(raw)
                break
            except Exception as error:
                elapsed = time.monotonic() - started
                if n < max_attempts and elapsed < case_timeout and _retryable(error):
                    time.sleep(min(30, 2**n) * (0.5 + random.random()))  # jittered backoff
                    continue
                kind = "timeout" if elapsed >= case_timeout else "api_error" if _retryable(error) else "harness_error"
                append(errors_path, {"prompt_id": case["id"], "rep": rep, "class": kind, "attempts": n, "error": repr(error)[:500]})
                return

        if call is not None and expected_model and call.model != expected_model:
            # a substituted model (e.g. a fallback) would make the comparison meaningless
            append(
                errors_path,
                {
                    "prompt_id": case["id"],
                    "rep": rep,
                    "class": "served_model_mismatch",
                    "attempts": n,
                    "model": call.model,
                    "usage": call.usage,
                },
            )
            return

        refused = call is not None and call.stop_reason == "refusal"
        truncated = call is not None and call.stop_reason == "max_tokens"
        if analysis is None and not refused and not truncated:
            append(errors_path, {"prompt_id": case["id"], "rep": rep, "class": "unparseable_output", "attempts": n})
            return
        row = {
            "prompt_id": case["id"],
            "rep": rep,
            "prompt": raw.title,
            "tags": case["tags"],
            "status": "truncated" if truncated else "ok",
            "stop_reason": call.stop_reason if call else None,
            "grade": grade(case["expected"], analysis, refused=refused),
            "model": call.model if call else "keywords",
            "usage": call.usage if call else None,
            "latency_s": call.latency_s if call else None,
            "attempts": n,
            "meta": {
                "expected": case["expected"],
                "predicted": asdict(analysis) if analysis else None,
                "off_vocabulary": sorted(s for s in (analysis.skills if analysis else []) if s not in SKILLS),
            },
        }
        trace = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": call.prompt if call else build_prompt(raw)},
            {"role": "assistant", "content": json.dumps(call.output if call else asdict(analysis), indent=2, ensure_ascii=False)},
        ]
        (out_dir / "traces" / f"{case['id']}_rep{rep}.json").write_text(json.dumps(trace, indent=1, ensure_ascii=False), encoding="utf-8")
        append(results_path, row)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(attempt, case, rep) for case, rep in todo]):
            future.result()

    summary = summarize(_read_jsonl(results_path), _read_jsonl(errors_path), n_cases=len(cases), reps=reps)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(summary_markdown(summary, out_dir.name), encoding="utf-8")
    return summary


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------- summaries ----------


def _case_means(rows: list[dict], metric: str) -> dict[str, float]:
    """Average each case over its reps, so the interval is over cases rather than inflated by reps."""
    per_case: dict[str, list[float]] = {}
    for r in rows:
        value = r["grade"].get(metric)
        if r["status"] == "ok" and value is not None:
            per_case.setdefault(r["prompt_id"], []).append(value)
    return {case: statistics.fmean(values) for case, values in per_case.items()}


def _interval(values: list[float]) -> tuple[float, float]:
    """Mean and 95% half-width (normal approximation over cases)."""
    if not values:
        return math.nan, math.nan
    mean = statistics.fmean(values)
    if len(values) < 2:
        return mean, math.nan
    return mean, 1.96 * statistics.stdev(values) / math.sqrt(len(values))


def cost_usd(rows: list[dict]) -> float | None:
    total = 0.0
    for r in rows:
        usage = r.get("usage")
        if not usage:
            continue
        price = PRICES.get(r["model"])
        if price is None:
            return None
        p_in, p_out = price
        total += (
            usage["input_tokens"] * p_in
            + usage["output_tokens"] * p_out
            + usage.get("cache_read_input_tokens", 0) * p_in * 0.1
            + usage.get("cache_creation_input_tokens", 0) * p_in * 1.25
        ) / 1e6
    return round(total, 4)


def summarize(rows: list[dict], errors: list[dict], n_cases: int, reps: int) -> dict:
    metrics = {}
    for m in METRICS:
        means = _case_means(rows, m)
        mean, half = _interval(list(means.values()))
        metrics[m] = {"mean": mean, "ci95": half, "cases": len(means)}
    latencies = [r["latency_s"] for r in rows if r.get("latency_s") is not None]
    usage_rows = [r["usage"] for r in rows if r.get("usage")]
    return {
        "cases": n_cases,
        "reps": reps,
        "rows": len(rows),
        "truncated": sum(r["status"] == "truncated" for r in rows),
        "errors": len(errors),
        "models": sorted({r["model"] for r in rows}),
        "metrics": metrics,
        "latency_s_median": statistics.median(latencies) if latencies else None,
        "output_tokens_mean": statistics.fmean(u["output_tokens"] for u in usage_rows) if usage_rows else None,
        "cost_usd": cost_usd(rows),
        "off_vocabulary": sorted({s for r in rows for s in r["meta"]["off_vocabulary"]}),
    }


def _fmt(mean: float, half: float) -> str:
    if math.isnan(mean):
        return "n/a"
    return f"{mean:.0%}" + ("" if math.isnan(half) else f" ± {half:.0%}")


def summary_markdown(summary: dict, name: str) -> str:
    lines = [
        f"## {name}",
        "",
        f"{summary['cases']} cases × {summary['reps']} rep(s), {summary['rows']} graded, "
        f"{summary['errors']} errors, {summary['truncated']} truncated. Model: {', '.join(summary['models']) or 'n/a'}.",
        "",
        "| Metric | Score (95% CI) | Cases |",
        "|---|---|---|",
    ]
    for m in METRICS:
        s = summary["metrics"][m]
        lines.append(f"| {LABELS[m]} | {_fmt(s['mean'], s['ci95'])} | {s['cases']} |")
    extras = []
    if summary["latency_s_median"] is not None:
        extras.append(f"median latency {summary['latency_s_median']:.1f} s")
    if summary["output_tokens_mean"] is not None:
        extras.append(f"{summary['output_tokens_mean']:.0f} output tokens per case")
    if summary["cost_usd"] is not None and summary["models"] != ["keywords"]:
        extras.append(f"total cost ${summary['cost_usd']:.2f}")
    if extras:
        lines += ["", "Per run: " + ", ".join(extras) + "."]
    return "\n".join(lines) + "\n"


def compare(a_dir: Path, b_dir: Path) -> str:
    """Paired comparison of two variants on the cases both completed."""
    a_rows, b_rows = _read_jsonl(a_dir / "results.jsonl"), _read_jsonl(b_dir / "results.jsonl")
    lines = [
        f"## {b_dir.name} vs {a_dir.name}",
        "",
        f"Paired over cases both variants graded; positive means {b_dir.name} is better (for Refused, positive means it refused more).",
        "",
        f"| Metric | {a_dir.name} | {b_dir.name} | Difference (95% CI) | Cases |",
        "|---|---|---|---|---|",
    ]
    for m in METRICS:
        a, b = _case_means(a_rows, m), _case_means(b_rows, m)
        shared = sorted(a.keys() & b.keys())
        diff_mean, diff_half = _interval([b[c] - a[c] for c in shared])
        a_mean, _ = _interval([a[c] for c in shared])
        b_mean, _ = _interval([b[c] for c in shared])
        diff = "n/a" if math.isnan(diff_mean) else f"{diff_mean:+.0%}" + ("" if math.isnan(diff_half) else f" ± {diff_half:.0%}")
        lines.append(f"| {LABELS[m]} | {_fmt(a_mean, math.nan)} | {_fmt(b_mean, math.nan)} | {diff} | {len(shared)} |")
    return "\n".join(lines) + "\n"


def cases_markdown(cases: list[dict]) -> str:
    """Human-readable view of the cases for review."""
    out = [
        "# Evaluation cases",
        "",
        f"{len(cases)} hand-written postings with expected answers. The companies are made up. The labels were written",
        "by hand together with the cases, so check them before trusting a score: a wrong label caps the score",
        "for reasons that have nothing to do with the analyzer.",
        "",
        "Skills marked *also acceptable* don't count against precision when predicted, and aren't needed for recall.",
        "Skills outside the vocabulary in `src/jobpulse/skills.py` are not scored.",
        "",
    ]
    out += ["| id | tags | required skills | seniority | work mode | salary |", "|---|---|---|---|---|---|"]
    for c in cases:
        e, s = c["expected"], c["expected"]["salary"]
        salary = f"{s['min']}–{s['max']} {s['currency']}/{s['period']}" if s else "none"
        skills = ", ".join(e["skills_required"]) or "–"
        out.append(f"| {c['id']} | {', '.join(c['tags'])} | {skills} | {e['seniority']} | {e['work_mode']} | {salary} |")
    for c in cases:
        p, e = c["posting"], c["expected"]
        out += ["", f"## {c['id']}", "", f"**{p['title']}**, {p['company']}, {p['location']}", "", "````text", p["description"], "````", ""]
        out.append(f"- Required skills: {', '.join(e['skills_required']) or 'none'}")
        if e["skills_allowed"]:
            out.append(f"- Also acceptable: {', '.join(e['skills_allowed'])}")
        out.append(f"- Seniority: {e['seniority']}; work mode: {e['work_mode']}")
        s = e["salary"]
        out.append(f"- Salary: {s['min']}–{s['max']} {s['currency']} per {s['period']}" if s else "- Salary: none stated")
        if c.get("note"):
            out.append(f"- Note: {c['note']}")
    return "\n".join(out) + "\n"
