from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

from .config import Settings
from .safe_sql import BUSINESS_SCHEMA
from .schemas import EvaluationCase, ModelAnswer


@dataclass(frozen=True)
class ProviderResult:
    answer: ModelAnswer
    latency_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    response_id: str | None = None


def estimate_cost(model: str, input_tokens: int, output_tokens: int, settings: Settings) -> float:
    prices = {
        "gpt-5.6-luna": (0.20, 1.20),
        "gpt-5.6-terra": (2.00, 12.00),
        "gpt-5.6-sol": (4.00, 20.00),
        "gpt-5.6": (4.00, 20.00),
    }
    input_price, output_price = prices.get(
        model,
        (settings.input_price_per_million, settings.output_price_per_million),
    )
    return round(
        input_tokens * input_price / 1_000_000 + output_tokens * output_price / 1_000_000,
        8,
    )


class FixtureProvider:
    """Deterministic, zero-cost provider used only for product and CI verification."""

    name = "fixture"

    async def generate(self, case: EvaluationCase, model: str, settings: Settings) -> ProviderResult:
        started = time.perf_counter()
        answer = ModelAnswer(
            answer=case.expected_answer,
            sql=case.expected_sql,
            explanation="Deterministic fixture output copied from the versioned evaluation case.",
            confidence=1.0,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        return ProviderResult(
            answer=answer,
            latency_ms=max(latency_ms, 0.01),
            input_tokens=0,
            output_tokens=0,
            estimated_cost_usd=0.0,
            response_id=None,
        )


class OpenAIProvider:
    name = "openai"

    def __init__(self) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your environment; never place keys in source code."
            )

    async def generate(self, case: EvaluationCase, model: str, settings: Settings) -> ProviderResult:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is not installed. Run: pip install -e '.[dev]'") from exc

        client = AsyncOpenAI()
        schema = ModelAnswer.model_json_schema()
        prompt = (
            f"DATABASE SCHEMA\n{BUSINESS_SCHEMA}\n\n"
            f"BUSINESS QUESTION\n{case.question}\n\n"
            "Produce the answer from one read-only SQLite query. Do not invent rows or use outside facts. "
            "The answer must state the result plainly."
        )
        started = time.perf_counter()
        response = await client.responses.create(
            model=model,
            instructions=(
                "You are a careful business-data analyst being evaluated for correctness. "
                "Return a structured answer and exactly one safe read-only SQLite SELECT query."
            ),
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "kerf_business_answer",
                    "strict": True,
                    "schema": schema,
                }
            },
            reasoning={"effort": settings.reasoning_effort},
            max_output_tokens=settings.max_output_tokens,
            store=False,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        if not response.output_text:
            raise RuntimeError("The model returned no text output")
        answer = ModelAnswer.model_validate(json.loads(response.output_text))
        usage = response.usage
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        return ProviderResult(
            answer=answer,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimate_cost(model, input_tokens, output_tokens, settings),
            response_id=getattr(response, "id", None),
        )


def build_provider(name: str) -> FixtureProvider | OpenAIProvider:
    if name == "fixture":
        return FixtureProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ValueError(f"Unsupported provider: {name}")

