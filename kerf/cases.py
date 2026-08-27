from __future__ import annotations

import json
from functools import lru_cache

from .config import settings
from .schemas import EvaluationCase


@lru_cache(maxsize=1)
def load_cases() -> tuple[EvaluationCase, ...]:
    path = settings.data_dir / "eval_cases.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = tuple(EvaluationCase.model_validate(item) for item in raw)
    ids = [case.id for case in cases]
    if len(cases) != 20:
        raise RuntimeError(f"Expected 20 evaluation cases, found {len(cases)}")
    if len(ids) != len(set(ids)):
        raise RuntimeError("Evaluation case IDs must be unique")
    return cases


def select_cases(case_ids: list[str] | None) -> list[EvaluationCase]:
    cases = list(load_cases())
    if case_ids is None:
        return cases
    by_id = {case.id: case for case in cases}
    missing = sorted(set(case_ids) - set(by_id))
    if missing:
        raise ValueError(f"Unknown evaluation cases: {', '.join(missing)}")
    return [by_id[case_id] for case_id in case_ids]

