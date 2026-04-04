from __future__ import annotations

from enum import StrEnum

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutionJobBackend(StrEnum):
    ARQ = "arq"
    INLINE = "inline"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENT_ATLAS_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Agent Atlas API"
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    openai_api_key: SecretStr | None = Field(
        default=None,
        repr=False,
        description="OpenAI API key used for live execution.",
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
    execution_job_backend: ExecutionJobBackend = Field(
        default=ExecutionJobBackend.ARQ,
        description="Background execution job backend. Use inline only for deterministic tests.",
    )
    execution_job_queue_url: str = Field(
        default="redis://127.0.0.1:6379/0",
        description="Redis DSN used by the Arq execution job queue.",
    )
    execution_job_queue_name: str = Field(
        default="agent-atlas:execution-jobs",
        description="Arq queue name used for control-plane background execution jobs.",
    )
    k8s_namespace: str = Field(
        default="agent-atlas-runs",
        description="Kubernetes namespace used for queued Atlas runner Jobs.",
    )
    k8s_service_account_name: str = Field(
        default="agent-atlas-runner",
        description="Service account used by Kubernetes runner Jobs.",
    )
    k8s_kubectl_command: list[str] = Field(
        default_factory=lambda: ["kubectl"],
        description="Command prefix used to talk to the Kubernetes API via kubectl.",
    )
    k8s_poll_interval_seconds: float = Field(
        default=1.0,
        description="Polling interval for Kubernetes Job and Pod status checks.",
    )
    k8s_heartbeat_interval_seconds: float = Field(
        default=5.0,
        description="Heartbeat interval while waiting on a Kubernetes runner Job.",
    )
    tracing_otlp_endpoint: str | None = Field(
        default=None,
        description="OTLP endpoint used for neutral runtime/control-plane trace export.",
    )
    tracing_otlp_timeout_seconds: float = Field(
        default=1.0,
        description="Timeout budget for a single OTLP trace export attempt.",
    )
    tracing_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Optional OTLP export headers.",
    )
    tracing_project_name: str = Field(
        default="agent-atlas",
        description="Logical tracing project name used for exported Atlas traces.",
    )
    phoenix_base_url: str | None = Field(
        default=None,
        description="Phoenix application base URL used to build backend-owned deep links.",
    )
    phoenix_api_key: SecretStr | None = Field(
        default=None,
        repr=False,
        description="Optional Phoenix API key used for OTLP export and deeplink resolution.",
    )


settings = Settings()
