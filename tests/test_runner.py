from pathlib import Path

import pytest

from kerf.config import Settings
from kerf.db import HistoryStore, initialize_business_database, initialize_history_database
from kerf.importing import import_run_report
from kerf.reporting import csv_report, markdown_report
from kerf.runner import EvaluationRunner, compare_runs


def temporary_settings(tmp_path: Path) -> Settings:
    data = tmp_path / "data"
    return Settings(
        project_root=tmp_path,
        data_dir=data,
        report_dir=tmp_path / "reports",
        static_dir=tmp_path / "static",
        business_db_path=data / "business.sqlite3",
        history_db_path=data / "kerf.sqlite3",
    )


@pytest.mark.asyncio
async def test_fixture_suite_passes_all_20_cases(tmp_path: Path) -> None:
    config = temporary_settings(tmp_path)
    config.ensure_directories()
    initialize_business_database(config.business_db_path)
    initialize_history_database(config.history_db_path)
    history = HistoryStore(config.history_db_path)

    run = await EvaluationRunner(config, history).run("fixture", "kerf-fixture-v1")

    assert run["case_count"] == 20
    assert run["passed_count"] == 20
    assert run["average_score"] == 100.0
    assert run["estimated_cost_usd"] == 0
    assert all(result["passed"] for result in run["results"])


@pytest.mark.asyncio
async def test_reports_and_comparison(tmp_path: Path) -> None:
    config = temporary_settings(tmp_path)
    config.ensure_directories()
    initialize_business_database(config.business_db_path)
    initialize_history_database(config.history_db_path)
    history = HistoryStore(config.history_db_path)
    runner = EvaluationRunner(config, history)
    first = await runner.run("fixture", "fixture-a", ["revenue_total", "no_show_rate"])
    second = await runner.run("fixture", "fixture-b", ["revenue_total", "no_show_rate"])

    comparison = compare_runs([first, second])
    assert comparison["common_case_count"] == 2
    assert "Deterministic fixture" in markdown_report(first)
    assert "case_id" in csv_report(first)


@pytest.mark.asyncio
async def test_completed_report_import_is_deduplicated(tmp_path: Path) -> None:
    source_config = temporary_settings(tmp_path / "source")
    source_config.ensure_directories()
    initialize_business_database(source_config.business_db_path)
    initialize_history_database(source_config.history_db_path)
    source_history = HistoryStore(source_config.history_db_path)
    source_run = await EvaluationRunner(source_config, source_history).run(
        "fixture", "import-test", ["revenue_total"]
    )

    target_path = tmp_path / "target" / "history.sqlite3"
    initialize_history_database(target_path)
    target_history = HistoryStore(target_path)
    source_url = "https://github.com/example/project/actions/runs/123"

    imported, was_new = import_run_report(target_history, source_run, source_url)
    duplicate, duplicate_was_new = import_run_report(target_history, source_run, source_url)

    assert was_new is True
    assert duplicate_was_new is False
    assert duplicate["id"] == imported["id"]
    assert imported["origin"] == "imported"
    assert imported["source_url"] == source_url
    assert imported["passed_count"] == 1
    assert len(target_history.list_runs()) == 1

    with pytest.raises(ValueError, match="absolute http or https URL"):
        import_run_report(target_history, source_run, "javascript:alert(1)")
