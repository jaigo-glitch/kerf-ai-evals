from __future__ import annotations

import json
from pathlib import Path

from .config import settings
from .schemas import LiveBaseline


def load_live_baselines(directory: Path | None = None) -> list[dict[str, object]]:
    """Load and validate committed summaries of successful live evaluations."""

    baseline_dir = directory or settings.data_dir / "baselines"
    if not baseline_dir.exists():
        return []

    baselines = []
    for path in sorted(baseline_dir.glob("*.json"), reverse=True):
        payload = json.loads(path.read_text(encoding="utf-8"))
        baseline = LiveBaseline.model_validate(payload)
        baselines.append(baseline.model_dump(mode="json"))
    return sorted(baselines, key=lambda item: str(item["recorded_at"]), reverse=True)
