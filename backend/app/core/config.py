from __future__ import annotations

from enum import StrEnum

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeMode(StrEnum):
    AUTO = "auto"
    LIVE = "live"
    MOCK = "mock"


class RunnerMode(StrEnum):
    AUTO = "auto"
    LOCAL = "local"
    DOCKER = "docker"
    MOCK = "mock"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AFLIGHT_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Agent Flight Recorder API"
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    runtime_mode: RuntimeMode = Field(
        default=RuntimeMode.AUTO,
        description=(
            "Execution mode: auto|live|mock. " "auto falls back to mock when OPENAI key missing."
        ),
    )
    runner_mode: RunnerMode = Field(
        default=RunnerMode.AUTO,
        description="Execution runner mode: auto|local|docker|mock.",
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AFLIGHT_OPENAI_API_KEY", "OPENAI_API_KEY"),
        repr=False,
        description="OpenAI API key used for live execution.",
    )
    seed_demo: bool | None = Field(
        default=None,
        description=(
            "Whether demo runs/datasets should be seeded on startup. "
            "Defaults to disabled in live mode and enabled otherwise."
        ),
    )
    runner_image: str = Field(
        default="agent-flight-recorder-backend:latest",
        description="Docker image used for isolated run execution.",
    )
    database_url: str | None = Field(
        default=None,
        description=(
            "State backend URL. sqlite:///path works; " "otherwise startup falls back to memory."
        ),
    )
    worker_name: str | None = Field(
        default=None,
        description="Optional worker name override for task consumers.",
    )
    worker_poll_interval_seconds: float = Field(
        default=1.0,
        description="Sleep interval between worker queue polls.",
    )
    worker_task_lease_seconds: int = Field(
        default=30,
        description="Lease duration before a running task can be reclaimed by another worker.",
    )

    def effective_runtime_mode(self, api_key: SecretStr | None = None) -> RuntimeMode:
        resolved_api_key = api_key if api_key is not None else self.openai_api_key
        if self.runtime_mode == RuntimeMode.MOCK:
            return RuntimeMode.MOCK
        if self.runtime_mode == RuntimeMode.LIVE:
            return RuntimeMode.LIVE
        return RuntimeMode.LIVE if resolved_api_key else RuntimeMode.MOCK

    def should_seed_demo(self) -> bool:
        if self.seed_demo is not None:
            return self.seed_demo
        return self.runtime_mode != RuntimeMode.LIVE

    def should_allow_mock_fallback(self, api_key: SecretStr | None = None) -> bool:
        if self.runner_mode == RunnerMode.MOCK:
            return True
        return self.effective_runtime_mode(api_key) != RuntimeMode.LIVE


settings = Settings()
