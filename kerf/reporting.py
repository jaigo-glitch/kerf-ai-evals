from __future__ import annotations

import csv
import io
import json
from typing import Any


def markdown_report(run: dict[str, Any]) -> str:
    provider_note = (
        "Deterministic fixture; no external model was called."
        if run["provider"] == "fixture"
        else "Live OpenAI API run."
    )
    lines = [
        f"# KERF Evaluation Report — Run {run['id']}",
        "",
        f"- Provider: `{run['provider']}` ({provider_note})",
        f"- Model: `{run['model']}`",
        f"- Created: {run['created_at']}",
        f"- Cases: {run['case_count']}",
        f"- Passed: {run['passed_count']}",
        f"- Average score: {run['average_score']:.2f}",
        f"- Average latency: {run['average_latency_ms']:.2f} ms",
        f"- Input/output tokens: {run['input_tokens']} / {run['output_tokens']}",
        f"- Estimated cost: ${run['estimated_cost_usd']:.6f}",
        "",
        "## Case results",
        "",
        "| Case | Score | Passed | Latency | Failures |",
        "|---|---:|:---:|---:|---|",
    ]
    for result in run["results"]:
        failures = ", ".join(result["detected_failures"]) or "—"
        lines.append(
            f"| {result['case_id']} | {result['score']:.2f} | "
            f"{'Yes' if result['passed'] else 'No'} | {result['latency_ms']:.2f} ms | {failures} |"
        )
    lines.extend(["", "## Evidence", ""])
    for result in run["results"]:
        lines.extend(
            [
                f"### {result['case_id']}",
                "",
                f"**Question:** {result['question']}",
                "",
                f"**Expected:** {result['expected_answer']}",
                "",
                f"**Model answer:** {result['model_answer']['answer'] if result['model_answer'] else 'No answer'}",
                "",
                "```sql",
                result["model_answer"]["sql"] if result["model_answer"] else "-- no SQL returned",
                "```",
                "",
            ]
        )
    lines.append("All company data in this report is synthetic.")
    return "\n".join(lines) + "\n"


def json_report(run: dict[str, Any]) -> str:
    return json.dumps(run, indent=2, sort_keys=True) + "\n"


def csv_report(run: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "run_id", "provider", "model", "case_id", "score", "passed", "latency_ms",
            "input_tokens", "output_tokens", "estimated_cost_usd", "failures", "error",
        ],
    )
    writer.writeheader()
    for result in run["results"]:
        writer.writerow(
            {
                "run_id": run["id"],
                "provider": run["provider"],
                "model": run["model"],
                "case_id": result["case_id"],
                "score": result["score"],
                "passed": result["passed"],
                "latency_ms": result["latency_ms"],
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "estimated_cost_usd": result["estimated_cost_usd"],
                "failures": "|".join(result["detected_failures"]),
                "error": result["error"] or "",
            }
        )
    return output.getvalue()

