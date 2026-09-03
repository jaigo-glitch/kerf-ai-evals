from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .config import settings
from .db import HistoryStore, initialize_business_database, initialize_history_database
from .importing import import_run_report
from .runner import EvaluationRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run KERF AI evaluation suites")
    parser.add_argument("command", choices=["run", "import-run"], nargs="?", default="run")
    parser.add_argument("--provider", choices=["fixture", "openai"], default="fixture")
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "xhigh", "max"],
        default=None,
    )
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument(
        "--report",
        action="append",
        dest="report_paths",
        help="Completed JSON run report to import; may be repeated",
    )
    parser.add_argument("--source-url", help="Actions run or other provenance URL")
    args = parser.parse_args()

    settings.ensure_directories()
    initialize_business_database(settings.business_db_path)
    initialize_history_database(settings.history_db_path)
    history = HistoryStore(settings.history_db_path)
    if args.command == "import-run":
        if not args.report_paths:
            parser.error("import-run requires at least one --report path")
        imported_runs = []
        for report_path in args.report_paths:
            path = Path(report_path)
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                run, imported = import_run_report(history, payload, args.source_url)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                parser.error(f"could not import {path}: {exc}")
            imported_runs.append(
                {
                    "id": run["id"],
                    "model": run["model"],
                    "imported": imported,
                    "source_url": run["source_url"],
                }
            )
        print(json.dumps(imported_runs, indent=2))
        return

    model = args.model or (
        "kerf-fixture-v1" if args.provider == "fixture" else settings.default_model
    )
    runner = EvaluationRunner(settings, history)
    result = asyncio.run(
        runner.run(args.provider, model, args.case_ids, args.reasoning_effort)
    )
    print(json.dumps({key: value for key, value in result.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
