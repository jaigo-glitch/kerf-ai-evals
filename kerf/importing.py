from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlsplit

from .db import HistoryStore
from .schemas import RunImport


def import_run_report(
    history: HistoryStore,
    payload: dict[str, Any],
    source_url: str | None = None,
) -> tuple[dict[str, Any], bool]:
    """Import a completed JSON report, returning the run and whether it was new."""

    if source_url:
        parsed_source = urlsplit(source_url)
        if parsed_source.scheme not in {"http", "https"} or not parsed_source.netloc:
            raise ValueError("source_url must be an absolute http or https URL")
    report = RunImport.model_validate(payload)
    normalized = report.model_dump(mode="json")
    fingerprint_payload = {key: value for key, value in normalized.items() if key != "id"}
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return history.import_completed_run(
        provider=report.provider,
        model=report.model,
        reasoning_effort=report.reasoning_effort,
        created_at=report.created_at,
        completed_at=report.completed_at,
        results=[result.model_dump(mode="json") for result in report.results],
        fingerprint=fingerprint,
        source_run_id=str(report.id) if report.id is not None else None,
        source_url=source_url,
    )
