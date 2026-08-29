from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kerf.config import settings
from kerf.db import HistoryStore, initialize_business_database, initialize_history_database
from kerf.reporting import json_report, markdown_report
from kerf.runner import EvaluationRunner, compare_runs


EFFORTS = ("none", "low", "medium", "high", "xhigh", "max")


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-")


def comparison_markdown(comparison: dict[str, Any]) -> str:
    lines = [
        "# KERF Live Model Comparison",
        "",
        "> This report contains live OpenAI API results against synthetic business data.",
        "",
        "| Run | Model | Reasoning | Passed | Score | Avg latency | Cost |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for run in comparison["run_summaries"]:
        lines.append(
            f"| {run['id']} | `{run['model']}` | `{run['reasoning_effort']}` | "
            f"{run['passed_count']}/{run['case_count']} | {run['average_score']:.2f} | "
            f"{run['average_latency_ms']:.2f} ms | ${run['estimated_cost_usd']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Case-by-case results",
            "",
            "| Case | Configuration A | Configuration B |",
            "|---|---|---|",
        ]
    )
    for case in comparison["cases"]:
        summaries = [
            f"{'PASS' if run['passed'] else 'FAIL'} · {run['score']:.2f} · "
            f"{run['latency_ms']:.2f} ms · ${run['cost_usd']:.6f}"
            for run in case["runs"]
        ]
        lines.append(f"| `{case['case_id']}` | {summaries[0]} | {summaries[1]} |")
    lines.extend(
        [
            "",
            "Failures are benchmark findings, not workflow errors. API, parsing, or execution errors "
            "still cause the workflow itself to fail.",
            "",
        ]
    )
    return "\n".join(lines)


def require_clean_execution(run: dict[str, Any]) -> None:
    errors = [
        f"{result['case_id']}: {result['error']}"
        for result in run["results"]
        if result.get("error")
    ]
    if errors:
        preview = "; ".join(errors[:3])
        remaining = len(errors) - 3
        suffix = f"; plus {remaining} more" if remaining > 0 else ""
        raise RuntimeError(
            f"Run {run['id']} ({run['model']}/{run['reasoning_effort']}) had "
            f"{len(errors)} execution error(s): {preview}{suffix}"
        )


async def execute(args: argparse.Namespace) -> int:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for a live comparison")
    if (args.model_a, args.effort_a) == (args.model_b, args.effort_b):
        raise ValueError("The two live comparison profiles must differ")

    settings.ensure_directories()
    initialize_business_database(settings.business_db_path)
    initialize_history_database(settings.history_db_path)
    history = HistoryStore(settings.history_db_path)
    runner = EvaluationRunner(settings, history)

    first = await runner.run("openai", args.model_a, reasoning_effort=args.effort_a)
    require_clean_execution(first)
    second = await runner.run("openai", args.model_b, reasoning_effort=args.effort_b)
    require_clean_execution(second)
    comparison = compare_runs([first, second])

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / f"live-comparison-{stamp}"

    (prefix.with_suffix(".json")).write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (prefix.with_suffix(".md")).write_text(
        comparison_markdown(comparison),
        encoding="utf-8",
    )
    for run in (first, second):
        label = safe_name(f"run-{run['id']}-{run['model']}-{run['reasoning_effort']}")
        (output_dir / f"{label}.json").write_text(json_report(run), encoding="utf-8")
        (output_dir / f"{label}.md").write_text(markdown_report(run), encoding="utf-8")

    summary = {
        "profiles": [
            {
                "model": run["model"],
                "reasoning_effort": run["reasoning_effort"],
                "passed": run["passed_count"],
                "cases": run["case_count"],
                "average_score": run["average_score"],
                "average_latency_ms": run["average_latency_ms"],
                "estimated_cost_usd": run["estimated_cost_usd"],
            }
            for run in (first, second)
        ],
        "report_prefix": str(prefix),
    }
    print(json.dumps(summary, indent=2))

    minimum = args.minimum_pass_rate
    pass_rates = [run["passed_count"] / run["case_count"] for run in (first, second)]
    return 2 if any(rate < minimum for rate in pass_rates) else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run and compare two live KERF model profiles")
    parser.add_argument("--model-a", default="gpt-5.6-luna")
    parser.add_argument("--effort-a", choices=EFFORTS, default="low")
    parser.add_argument("--model-b", default="gpt-5.6-terra")
    parser.add_argument("--effort-b", choices=EFFORTS, default="low")
    parser.add_argument("--output-dir", default="reports")
    parser.add_argument("--minimum-pass-rate", type=float, default=0.0)
    args = parser.parse_args()
    if not 0 <= args.minimum_pass_rate <= 1:
        parser.error("--minimum-pass-rate must be between 0 and 1")
    raise SystemExit(asyncio.run(execute(args)))


if __name__ == "__main__":
    main()
