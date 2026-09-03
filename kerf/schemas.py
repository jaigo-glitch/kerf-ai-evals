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
    score: float = Field(ge=0, le=100)
    passed: bool
    detected_failures: list[str]
    latency_ms: float = Field(ge=0)
    input_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    reasoning_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)
    response_id: str | None = None
    error: str | None = None


class RunImport(BaseModel):
    """Validated shape of a completed JSON evidence report."""

    model_config = ConfigDict(extra="ignore")

    id: int | str | None = None
    created_at: str
    completed_at: str | None = None
    provider: Literal["fixture", "openai"]
    model: str = Field(min_length=1, max_length=160)
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"]
    status: Literal["completed"]
    results: list[CaseResult] = Field(min_length=1)


class BaselineProfile(BaseModel):
    model: str
    reasoning_effort: str
    passed_count: int = Field(ge=0)
    average_score: float = Field(ge=0, le=100)
    average_latency_ms: float = Field(ge=0)
    input_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    reasoning_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)


class LiveBaseline(BaseModel):
    schema_version: Literal[1]
    id: str
    title: str
    recorded_at: str
    workflow: str
    workflow_attempt: int = Field(ge=1)
    actions_run_url: str
    artifact_name: str
    artifact_expires_on: str
    synthetic_data: Literal[True]
    case_count: int = Field(gt=0)
    profiles: list[BaselineProfile] = Field(min_length=2)
    findings: list[str] = Field(default_factory=list)
