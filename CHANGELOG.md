# Changelog

## 0.3.0 — 2026-09-03

- Published the first successful, source-linked live Luna-versus-Terra baseline in the dashboard.
- Added validated, deduplicating import of completed JSON run reports into normal run history.
- Labeled imported evidence and linked it back to its GitHub Actions source.
- Marked the live milestone complete; the five-person beta milestone remains open.

## 0.2.0 — 2026-08-29

- Added a manual GitHub Actions workflow for two-profile live model comparisons.
- Added per-run reasoning configuration and cached/reasoning token telemetry.
- Added response IDs and cache-aware cost estimates to evidence reports.
- Added adapter-level tests that validate the OpenAI structured-output request without API spend.

## 0.1.0 — 2026-08-27

- Added FastAPI API and interactive evidence dashboard.
- Added OpenAI Responses API structured-output adapter.
- Added deterministic fixture provider for CI and zero-cost testing.
- Added synthetic service-business database and 20 evaluation cases.
- Added safe read-only SQL execution and deterministic scoring.
- Added run history, comparisons, reports, feedback, issues, and tracker metrics.
