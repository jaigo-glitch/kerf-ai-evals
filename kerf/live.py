from __future__ import annotations

from typing import Any


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
