"""Settings from config/settings.yaml; env RUN_MODE overrides run_mode; API key from env only."""

import os
from datetime import datetime
from functools import lru_cache
from typing import Literal

import yaml
from pydantic import BaseModel

from trusted_service_agent.paths import CONFIG

RunMode = Literal["live", "record", "replay"]


class RateLimitsCfg(BaseModel):
    default_rpm: int
    max_concurrency: int

    def rpm_for(self, model: str) -> int:
        return self.default_rpm


class RetryCfg(BaseModel):
    max_attempts: int
    base_seconds: float
    cap_seconds: float
    max_wait_seconds: float


class Settings(BaseModel):
    run_mode: RunMode
    models: dict[str, list[str]]
    temperature: dict[str, float]
    max_output_tokens: dict[str, int]
    thinking_level: dict[str, str | int]
    router: dict[str, float]
    rate_limits: RateLimitsCfg
    retry: RetryCfg
    timeout_seconds: float
    paths: dict[str, str]
    demo_now: datetime
    stale_after_minutes: int


@lru_cache
def settings() -> Settings:
    raw = yaml.safe_load((CONFIG / "settings.yaml").read_text(encoding="utf-8"))
    raw["run_mode"] = os.environ.get("RUN_MODE", raw["run_mode"])
    return Settings.model_validate(raw)


def gemini_api_key() -> str:
    """Read `GEMINI_API_KEY` from the environment at call time. Never stored or logged."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set; live and record modes need it")
    return key
