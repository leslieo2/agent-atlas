from __future__ import annotations

from enum import StrEnum

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeMode(StrEnum):
    AUTO = "auto"
    LIVE = "live"
    MOCK = "mock"


class TraceBackendMode(StrEnum):
    STATE = "state"
    PHOENIX = "phoenix"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENT_ATLAS_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Agent Atlas API"
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    runtime_mode: RuntimeMode = Field(
        default=RuntimeMode.AUTO,
        description=(
            "Execution mode: auto|live|mock. " "auto falls back to mock when OPENAI key missing."
        ),
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AGENT_ATLAS_OPENAI_API_KEY", "OPENAI_API_KEY"),
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
    control_plane_database_url: str | None = Field(
        default=None,
        description=("Control plane database URL. Supports sqlite:///path and postgresql:// URLs."),
    )
    data_plane_database_url: str | None = Field(
        default=None,
        description=("Data plane database URL. Supports sqlite:///path and postgresql:// URLs."),
    )
    control_plane_database_schema: str = Field(
        default="control_plane",
        description="Schema name used for control-plane tables when PostgreSQL is configured.",
    )
    data_plane_database_schema: str = Field(
        default="data_plane",
        description="Schema name used for data-plane tables when PostgreSQL is configured.",
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
    trace_backend: TraceBackendMode = Field(
        default=TraceBackendMode.STATE,
        validation_alias=AliasChoices(
            "AGENT_ATLAS_TRACING_BACKEND",
            "AGENT_ATLAS_TRACE_BACKEND",
        ),
        description="Read-side trace backend mode: state|phoenix.",
    )
    tracing_otlp_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AGENT_ATLAS_TRACING_OTLP_ENDPOINT"),
        description="OTLP endpoint used for neutral runtime/control-plane trace export.",
    )
    tracing_headers: dict[str, str] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("AGENT_ATLAS_TRACING_HEADERS"),
        description="Optional OTLP export headers.",
    )
    tracing_project_name: str = Field(
        default="agent-atlas",
        validation_alias=AliasChoices("AGENT_ATLAS_TRACING_PROJECT_NAME"),
        description="Logical tracing project name used for exported Atlas traces.",
    )
    phoenix_base_url: str | None = Field(
        default=None,
        description="Phoenix application base URL used to build backend-owned deep links.",
    )
    phoenix_api_key: SecretStr | None = Field(
        default=None,
        repr=False,
        description="Optional Phoenix API key used for export and query clients.",
    )
    phoenix_query_limit: int = Field(
        default=500,
        description="Maximum number of Phoenix spans to fetch when reconstructing a run trace.",
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


settings = Settings()
