from __future__ import annotations

from typing import Any

from .cases import select_cases
from .config import Settings
from .db import HistoryStore
from .providers import build_provider
from .safe_sql import SafeSQLExecutor, UnsafeQueryError
from .schemas import CaseResult, EvaluationCase


class EvaluationRunner:
    def __init__(self, settings: Settings, history: HistoryStore):
        self.settings = settings
        self.history = history
        self.sql = SafeSQLExecutor(settings.business_db_path)

    async def run(
        self,
        provider_name: str,
        model: str,
        case_ids: list[str] | None = None,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        cases = select_cases(case_ids)
        provider = build_provider(provider_name)
        resolved_effort = reasoning_effort or self.settings.reasoning_effort
        run_id = self.history.create_run(provider_name, model, len(cases), resolved_effort)
        results: list[dict[str, Any]] = []
        try:
            for case in cases:
                result = await self._run_case(case, provider, model, resolved_effort)
                results.append(result.model_dump(mode="json"))
            self.history.complete_run(run_id, results)
        except Exception as exc:
            self.history.fail_run(run_id, str(exc))
            raise
        run = self.history.get_run(run_id)
        if run is None:
            raise RuntimeError("Completed run could not be loaded")
        return run

    async def _run_case(
        self,
        case: EvaluationCase,
        provider: Any,
        model: str,
        reasoning_effort: str,
    ) -> CaseResult:
        expected_rows = self.sql.execute(case.expected_sql)
        provider_result = None
        actual_rows: list[dict[str, Any]] | None = None
        failures: list[str] = []
        score = 0.0
        passed = False
        error: str | None = None
        try:
            provider_result = await provider.generate(
                case,
                model,
                self.settings,
                reasoning_effort,
            )
            actual_rows = self.sql.execute(provider_result.answer.sql)
            from .scoring import score_answer

            score, passed, failures = score_answer(
                case, provider_result.answer, expected_rows, actual_rows
            )
        except UnsafeQueryError as exc:
            failures.append("unsafe_or_invalid_sql")
            error = str(exc)
        except Exception as exc:
            failures.append("provider_or_parse_error")
            error = str(exc)

        return CaseResult(
            case_id=case.id,
            question=case.question,
            expected_answer=case.expected_answer,
            expected_sql=case.expected_sql,
            model_answer=provider_result.answer if provider_result else None,
            model_sql_rows=actual_rows,
            expected_sql_rows=expected_rows,
            score=score,
            passed=passed,
            detected_failures=failures,
            latency_ms=provider_result.latency_ms if provider_result else 0.0,
            input_tokens=provider_result.input_tokens if provider_result else 0,
            cached_input_tokens=provider_result.cached_input_tokens if provider_result else 0,
            output_tokens=provider_result.output_tokens if provider_result else 0,
            reasoning_tokens=provider_result.reasoning_tokens if provider_result else 0,
            estimated_cost_usd=provider_result.estimated_cost_usd if provider_result else 0.0,
            response_id=provider_result.response_id if provider_result else None,
            error=error,
        )


def compare_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if len(runs) < 2:
        raise ValueError("At least two completed runs are required for comparison")
    case_ids = sorted(
        set.intersection(*(set(result["case_id"] for result in run["results"]) for run in runs))
    )
    comparison_rows = []
    for case_id in case_ids:
        row: dict[str, Any] = {"case_id": case_id, "runs": []}
        for run in runs:
            result = next(item for item in run["results"] if item["case_id"] == case_id)
            row["runs"].append(
                {
                    "run_id": run["id"],
                    "model": run["model"],
                    "reasoning_effort": run["reasoning_effort"],
                    "score": result["score"],
                    "passed": result["passed"],
                    "latency_ms": result["latency_ms"],
                    "cost_usd": result["estimated_cost_usd"],
                }
            )
        comparison_rows.append(row)
    return {
        "run_summaries": [
            {
                key: run[key]
                for key in (
                    "id", "provider", "model", "reasoning_effort", "case_count",
                    "passed_count", "average_score", "average_latency_ms",
                    "estimated_cost_usd", "created_at",
                )
            }
            for run in runs
        ],
        "common_case_count": len(case_ids),
        "cases": comparison_rows,
    }
