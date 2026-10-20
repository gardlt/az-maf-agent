"""Trusted configuration, never model or request supplied."""

import json
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    input_bytes: int = Field(gt=0, le=16384)
    context_tokens: int = Field(gt=0, le=16000)
    output_tokens: int = Field(gt=0, le=2000)
    run_tokens: int = Field(gt=0, le=24000)
    turns: int = Field(gt=0, le=8)
    retries: int = Field(ge=0, le=2)
    run_seconds: float = Field(gt=0, le=120, allow_inf_nan=False)
    call_seconds: float = Field(gt=0, le=30, allow_inf_nan=False)
    history_bytes: int = Field(gt=0, le=65536)
    history_tokens: int = Field(gt=0, le=16000)
    idle_seconds: float = Field(gt=0, allow_inf_nan=False)
    lifetime_seconds: float = Field(gt=0, allow_inf_nan=False)
    run_usd: float = Field(gt=0, le=0.25, allow_inf_nan=False)
    daily_usd: float = Field(gt=0, le=5, allow_inf_nan=False)
    per_user_parallel: int = Field(gt=0, le=2)
    parallel: int = Field(gt=0, le=10)
    max_sessions: int = Field(gt=0, le=1000)


class ModelRoute(BaseModel):
    """Trusted deployment metadata; routes cannot change origin, identity or limits."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    deployment: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    api_version: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}(-preview)?$")
    reasoning_effort: Literal["minimal", "low", "medium", "high"]
    input_usd_per_million: float = Field(gt=0, allow_inf_nan=False)
    output_usd_per_million: float = Field(gt=0, allow_inf_nan=False)
    model_context_tokens: int = Field(gt=0)


class RoutingPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    version: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,100}$")
    mode: Literal["auto", "routine", "reasoning"] = "auto"
    routine: ModelRoute
    reasoning: ModelRoute


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    policy_version: str = Field(min_length=1, max_length=100)
    mode: Literal["fake", "azure"]
    limits: Limits
    endpoint: str | None = None
    deployment: str | None = None
    api_version: str | None = None
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None
    input_usd_per_million: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    output_usd_per_million: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    model_context_tokens: int | None = Field(default=None, gt=0)
    managed_identity_client_id: str | None = None
    routing: RoutingPolicy | None = None

    @model_validator(mode="after")
    def live_contract(self):
        if self.mode == "azure":
            import re

            if not all(
                (self.endpoint, self.deployment, self.api_version, self.model_context_tokens)
            ):
                raise ValueError("live model configuration incomplete")
            u = urlsplit(self.endpoint)
            if (
                u.scheme != "https"
                or not u.hostname
                or not u.hostname.endswith(".openai.azure.com")
                or u.port not in (None, 443)
                or u.username
                or u.password
                or u.query
                or u.fragment
                or u.path not in ("", "/")
            ):
                raise ValueError("expected approved Azure OpenAI resource origin")
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", self.deployment):
                raise ValueError("invalid configured deployment")
            if self.input_usd_per_million is None or self.output_usd_per_million is None:
                raise ValueError("approved pricing required")
            if self.limits.context_tokens + self.limits.output_tokens > self.model_context_tokens:
                raise ValueError("context plus output exceeds approved model window")
        if self.routing is not None:
            if self.mode != "azure":
                raise ValueError("routing requires approved Azure deployments")
            for route in (self.routing.routine, self.routing.reasoning):
                if (
                    self.limits.context_tokens + self.limits.output_tokens
                    > route.model_context_tokens
                ):
                    raise ValueError("route context window too small")
        return self


def load_settings(path: str) -> Settings:
    # No credentials belong in this file. Custom files must specify every limit.
    return Settings.model_validate(json.loads(Path(path).read_text()))
