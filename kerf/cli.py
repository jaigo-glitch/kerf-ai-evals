from __future__ import annotations

import argparse
import asyncio
import json

from .config import settings
from .db import HistoryStore, initialize_business_database, initialize_history_database
from .runner import EvaluationRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run KERF AI evaluation suites")
    parser.add_argument("run", nargs="?", default="run")
    parser.add_argument("--provider", choices=["fixture", "openai"], default="fixture")
    parser.add_argument("--model", default=None)
    parser.add_argument("--case", action="append", dest="case_ids")
    args = parser.parse_args()

    settings.ensure_directories()
    initialize_business_database(settings.business_db_path)
    initialize_history_database(settings.history_db_path)
    model = args.model or ("kerf-fixture-v1" if args.provider == "fixture" else settings.default_model)
    runner = EvaluationRunner(settings, HistoryStore(settings.history_db_path))
    result = asyncio.run(runner.run(args.provider, model, args.case_ids))
    print(json.dumps({key: value for key, value in result.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()

