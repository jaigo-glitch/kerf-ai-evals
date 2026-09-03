from fastapi.testclient import TestClient

from kerf.main import app


def test_health_cases_run_and_download() -> None:
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["evaluation_cases"] == 20
        assert health.json()["live_baselines"] >= 1

        baselines = client.get("/api/baselines")
        assert baselines.status_code == 200
        assert baselines.json()[0]["profiles"][0]["model"] == "gpt-5.6-luna"
        assert baselines.json()[0]["actions_run_url"].endswith("/33786781766")

        cases = client.get("/api/cases")
        assert cases.status_code == 200
        assert len(cases.json()) == 20

        run = client.post(
            "/api/runs",
            json={"provider": "fixture", "case_ids": ["revenue_total"]},
        )
        assert run.status_code == 201
        run_id = run.json()["id"]
        assert run.json()["passed_count"] == 1

        report = client.get(f"/api/reports/{run_id}.md")
        assert report.status_code == 200
        assert "KERF Evaluation Report" in report.text


def test_live_run_without_key_is_blocked(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(app) as client:
        response = client.post(
            "/api/runs",
            json={"provider": "openai", "model": "gpt-5.6-luna", "case_ids": ["revenue_total"]},
        )
        assert response.status_code == 503
        assert "OPENAI_API_KEY" in response.json()["detail"]
