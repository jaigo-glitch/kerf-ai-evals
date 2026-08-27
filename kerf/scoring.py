from __future__ import annotations

import json
import re
from typing import Any

from .schemas import EvaluationCase, ModelAnswer


def _canonical(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, str):
        return value.strip().lower()
    return value


def normalize_rows(rows: list[dict[str, Any]]) -> list[list[Any]]:
    normalized: list[list[Any]] = []
    for row in rows:
        normalized.append([_canonical(value) for value in row.values()])
    return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, default=str))


def _keyword_present(keyword: str, answer: str) -> bool:
    clean_answer = re.sub(r"[$,%]", "", answer.lower())
    clean_keyword = re.sub(r"[$,%]", "", keyword.lower())
    return clean_keyword in clean_answer


def score_answer(
    case: EvaluationCase,
    model_answer: ModelAnswer,
    expected_rows: list[dict[str, Any]],
    actual_rows: list[dict[str, Any]],
) -> tuple[float, bool, list[str]]:
    failures: list[str] = []
    expected_normalized = normalize_rows(expected_rows)
    actual_normalized = normalize_rows(actual_rows)
    result_matches = actual_normalized == expected_normalized
    score = 75.0 if result_matches else 0.0
    if not result_matches:
        failures.append("sql_result_mismatch")

    if case.answer_keywords:
        matched = sum(
            1 for keyword in case.answer_keywords if _keyword_present(keyword, model_answer.answer)
        )
        score += 20.0 * matched / len(case.answer_keywords)
        for keyword in case.answer_keywords:
            if not _keyword_present(keyword, model_answer.answer):
                failures.append(f"missing_answer_fact:{keyword}")
    else:
        score += 20.0

    if model_answer.explanation.strip():
        score += 5.0
    else:
        failures.append("blank_explanation")

    rounded = round(score, 2)
    return rounded, bool(result_matches and rounded >= 85.0), failures

