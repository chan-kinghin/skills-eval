"""Data models for SkillEval."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class ModelEntry(BaseModel):
    """A model in the catalog."""

    name: str
    provider: str
    endpoint: str
    input_cost_per_m: float
    output_cost_per_m: float
    env_key: str
    context_window: int = 128_000
    # For ad-hoc models where the API key is provided directly
    api_key: str | None = None

    @classmethod
    def adhoc(
        cls,
        *,
        endpoint: str,
        api_key: str | None,
        model_name: str,
        input_cost: float = 0.0,
        output_cost: float = 0.0,
        context_window: int = 128_000,
    ) -> "ModelEntry":
        """Create an ad-hoc model entry for arbitrary OpenAI-compatible endpoints.

        Defaults:
        - provider: "adhoc"
        - env_key: "_ADHOC_" (sentinel; key is stored in the entry)
        - costs default to $0
        - context window defaults to 128k
        """
        return cls(
            name=model_name,
            provider="adhoc",
            endpoint=endpoint,
            input_cost_per_m=input_cost,
            output_cost_per_m=output_cost,
            env_key="_ADHOC_",
            context_window=context_window,
            api_key=api_key,
        )


class TaskConfig(BaseModel):
    """Configuration for a task (from config.yaml)."""

    comparator: str = "json_exact"
    custom_script: str | None = None
    trials: int = 5
    timeout: int = 60
    temperature: float = 0.0
    max_tokens: int = 4096
    output_format: str = "json"


class TaskFolder(BaseModel):
    """Validated representation of a task directory."""

    model_config = {"arbitrary_types_allowed": True}

    path: Path
    input_files: list[Path]
    expected_files: list[Path]
    config: TaskConfig
    skill: str | None = None
    prompt: str | None = None
    meta_skills: dict[str, str] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response from a model API call."""

    content: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    model_version: str | None = None
    finish_reason: str | None = None

    @field_validator("input_tokens", "output_tokens")
    @classmethod
    def _tokens_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Token count must be non-negative")
        return v

    @field_validator("latency_seconds")
    @classmethod
    def _latency_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Latency must be non-negative")
        return v


class TrialResult(BaseModel):
    """Result of a single trial."""

    model: str
    trial_number: int
    passed: bool
    output_text: str = ""
    diff: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    latency_seconds: float = 0.0
    error: str | None = None
    finish_reason: str | None = None


class ModelResult(BaseModel):
    """Aggregated result for one model across all trials."""

    model: str
    pass_rate: float
    trials: list[TrialResult]
    avg_cost: float
    avg_latency: float
    total_cost: float
    context_window: int = 0


class MatrixCell(BaseModel):
    """Result for a creator x executor pair."""

    creator: str
    executor: str
    generated_skill: str
    result: ModelResult


class ChainCell(BaseModel):
    """Result for a meta-skill x creator x executor triple."""

    meta_skill_name: str
    creator: str
    executor: str
    generated_skill: str
    result: ModelResult


class RunSummary(BaseModel):
    """Complete summary of an evaluation run."""

    mode: str  # "run" | "matrix" | "chain"
    task_path: str
    timestamp: str
    model_results: list[ModelResult] = Field(default_factory=list)
    matrix_results: list[MatrixCell] = Field(default_factory=list)
    chain_results: list[ChainCell] = Field(default_factory=list)
    recommendation: str | None = None
