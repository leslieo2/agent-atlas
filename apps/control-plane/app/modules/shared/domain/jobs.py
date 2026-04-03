from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ExecutionJobKind(str, Enum):
    RUN_EXECUTION = "run_execution_job"
    EXPERIMENT_EXECUTION = "execute_experiment_job"
    EXPERIMENT_AGGREGATION = "refresh_experiment_job"


class EnqueuedExecutionJob(BaseModel):
    job_id: str
    kind: ExecutionJobKind
    kwargs: dict[str, Any]
