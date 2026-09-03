from __future__ import annotations

import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__
from .baselines import load_live_baselines
from .cases import load_cases
from .config import settings
from .db import HistoryStore, initialize_business_database, initialize_history_database
from .reporting import csv_report, json_report, markdown_report
from .runner import EvaluationRunner, compare_runs
from .safe_sql import BUSINESS_SCHEMA
from .schemas import FeedbackRequest, IssueRequest, RunRequest


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.ensure_directories()
    initialize_business_database(settings.business_db_path)
    initialize_history_database(settings.history_db_path)
    load_cases()
    load_live_baselines()
    yield


app = FastAPI(
    title="KERF",
    summary="Evidence-first evaluation infrastructure for business-data AI agents.",
    version=__version__,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")


def store() -> HistoryStore:
    return HistoryStore(settings.history_db_path)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(settings.static_dir / "index.html")


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "version": __version__,
        "evaluation_cases": len(load_cases()),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "synthetic_data": True,
        "live_baselines": len(load_live_baselines()),
    }


@app.get("/api/schema")
async def schema() -> dict[str, str]:
    return {"schema": BUSINESS_SCHEMA}


@app.get("/api/cases")
async def cases() -> list[dict[str, object]]:
    return [case.model_dump(mode="json") for case in load_cases()]


@app.get("/api/baselines")
async def baselines() -> list[dict[str, object]]:
    return load_live_baselines()


@app.post("/api/runs", status_code=201)
async def create_run(request: RunRequest) -> dict[str, object]:
    model = request.model or (
        "kerf-fixture-v1" if request.provider == "fixture" else settings.default_model
    )
    try:
        runner = EvaluationRunner(settings, store())
        return await runner.run(
            request.provider,
            model,
            request.case_ids,
            request.reasoning_effort,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/runs")
async def list_runs(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, object]]:
    return store().list_runs(limit)


@app.get("/api/runs/{run_id}")
async def get_run(run_id: int) -> dict[str, object]:
    run = store().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/api/compare")
async def compare(run_ids: str = Query(description="Comma-separated completed run IDs")) -> dict[str, object]:
    try:
        ids = [int(value.strip()) for value in run_ids.split(",") if value.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="run_ids must contain integers") from exc
    if len(ids) < 2 or len(ids) > 5:
        raise HTTPException(status_code=422, detail="Provide between two and five run IDs")
    runs = []
    for run_id in ids:
        run = store().get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        if run["status"] != "completed":
            raise HTTPException(status_code=409, detail=f"Run {run_id} is not completed")
        runs.append(run)
    return compare_runs(runs)


@app.get("/api/reports/{run_id}.{report_format}")
async def download_report(run_id: int, report_format: str) -> Response:
    run = store().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    builders = {
        "md": (markdown_report, "text/markdown; charset=utf-8"),
        "json": (json_report, "application/json"),
        "csv": (csv_report, "text/csv; charset=utf-8"),
    }
    if report_format not in builders:
        raise HTTPException(status_code=404, detail="Use md, json, or csv")
    builder, media_type = builders[report_format]
    return Response(
        content=builder(run),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="kerf-run-{run_id}.{report_format}"'},
    )


@app.post("/api/feedback", status_code=201)
async def add_feedback(request: FeedbackRequest) -> dict[str, object]:
    feedback_id = store().add_feedback(request.model_dump(mode="json"))
    return {"id": feedback_id, "status": "recorded", "synthetic_data": False}


@app.post("/api/issues", status_code=201)
async def add_issue(request: IssueRequest) -> dict[str, object]:
    issue_id = store().add_issue(request.model_dump(mode="json"))
    return {"id": issue_id, "status": "open"}


@app.get("/api/releases")
async def releases() -> list[dict[str, object]]:
    return store().list_releases()


def _git_commit_count(project_root: Path) -> int:
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        return int(result.stdout.strip())
    except (subprocess.SubprocessError, ValueError, FileNotFoundError):
        return 0


@app.get("/api/tracker")
async def tracker() -> dict[str, object]:
    metrics = store().tracker_metrics()
    metrics["git_commits"] = _git_commit_count(settings.project_root)
    metrics["github_repository_public"] = True
    return metrics
