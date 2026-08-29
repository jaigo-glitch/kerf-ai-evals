from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvaluationCase(BaseModel):
    id: str
    title: str
    category: str
    difficulty: Literal["basic", "intermediate", "advanced"]
    question: str
    expected_sql: str
    expected_answer: str
    answer_keywords: list[str] = Field(default_factory=list)
    tolerance: float = 0.001


class ModelAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    sql: str
    explanation: str
    confidence: float = Field(ge=0, le=1)


class RunRequest(BaseModel):
    provider: Literal["fixture", "openai"] = "fixture"
    model: str | None = None
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] | None = None
    case_ids: list[str] | None = None

    @field_validator("case_ids")
    @classmethod
    def reject_empty_case_list(cls, value: list[str] | None) -> list[str] | None:
        if value == []:
            raise ValueError("case_ids must be omitted or contain at least one case")
        return value


class FeedbackRequest(BaseModel):
    tester_alias: str = Field(min_length=2, max_length=80)
    role: str = Field(min_length=2, max_length=100)
    rating: int = Field(ge=1, le=5)
    feedback: str = Field(min_length=10, max_length=3000)
    consent_to_quote: bool = False


class IssueRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=5, max_length=3000)
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class CaseResult(BaseModel):
    case_id: str
    question: str
    expected_answer: str
    expected_sql: str
    model_answer: ModelAnswer | None
    model_sql_rows: list[dict[str, Any]] | None
    expected_sql_rows: list[dict[str, Any]]
    score: float
    passed: bool
    detected_failures: list[str]
    latency_ms: float
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    estimated_cost_usd: float
    response_id: str | None = None
    error: str | None = None
