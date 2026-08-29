import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from kerf.config import Settings
from kerf.providers import OpenAIProvider, estimate_cost
from kerf.schemas import EvaluationCase
from scripts.run_live_comparison import require_clean_execution


class FakeResponses:
    def __init__(self) -> None:
        self.request = None

    async def create(self, **kwargs):
        self.request = kwargs
        answer = {
            "answer": "The result is 1.",
            "sql": "SELECT 1 AS result",
            "explanation": "The query returns the requested value.",
            "confidence": 0.99,
        }
        return SimpleNamespace(
            id="resp_test_123",
            status="completed",
            output_text=json.dumps(answer),
            usage=SimpleNamespace(
                input_tokens=1_000,
                output_tokens=500,
                input_tokens_details=SimpleNamespace(cached_tokens=200),
                output_tokens_details=SimpleNamespace(reasoning_tokens=125),
            ),
        )


def settings(tmp_path: Path) -> Settings:
    return Settings(
        project_root=tmp_path,
        data_dir=tmp_path / "data",
        report_dir=tmp_path / "reports",
        static_dir=tmp_path / "static",
        business_db_path=tmp_path / "data" / "business.sqlite3",
        history_db_path=tmp_path / "data" / "kerf.sqlite3",
    )


@pytest.mark.asyncio
async def test_openai_provider_sends_structured_request_and_records_usage(tmp_path: Path) -> None:
    responses = FakeResponses()
    provider = OpenAIProvider(client=SimpleNamespace(responses=responses))
    case = EvaluationCase(
        id="test_case",
        title="Test case",
        category="test",
        difficulty="basic",
        question="Return one.",
        expected_sql="SELECT 1 AS result",
        expected_answer="The result is 1.",
    )

    result = await provider.generate(
        case,
        "gpt-5.6-luna",
        settings(tmp_path),
        reasoning_effort="medium",
    )

    assert responses.request["model"] == "gpt-5.6-luna"
    assert responses.request["reasoning"] == {"effort": "medium"}
    assert responses.request["text"]["format"]["type"] == "json_schema"
    assert responses.request["text"]["format"]["strict"] is True
    assert responses.request["store"] is False
    assert result.response_id == "resp_test_123"
    assert result.cached_input_tokens == 200
    assert result.reasoning_tokens == 125
    assert result.estimated_cost_usd == 0.000764


def test_cost_estimate_uses_cached_input_discount(tmp_path: Path) -> None:
    result = estimate_cost(
        "gpt-5.6-luna",
        input_tokens=1_000_000,
        cached_input_tokens=250_000,
        output_tokens=100_000,
        settings=settings(tmp_path),
    )

    assert result == 0.275


def test_live_comparison_rejects_execution_errors() -> None:
    run = {
        "id": 8,
        "model": "gpt-5.6-luna",
        "reasoning_effort": "low",
        "results": [
            {"case_id": "revenue_total", "error": "API request failed"},
            {"case_id": "booking_count", "error": None},
        ],
    }

    with pytest.raises(RuntimeError, match="1 execution error"):
        require_clean_execution(run)
