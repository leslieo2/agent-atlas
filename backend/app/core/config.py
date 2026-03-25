from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Agent Flight Recorder API"
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    runtime_mode: str = Field(
        default="auto",
        description=(
            "Execution mode: auto|live|mock. " "auto falls back to mock when OPENAI key missing."
        ),
    )
    runner_mode: str = Field(
        default="auto",
        description="Execution runner mode: auto|local|docker|mock.",
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

    class Config:
        env_prefix = "AFLIGHT_"
        env_file = ".env"


settings = Settings()
