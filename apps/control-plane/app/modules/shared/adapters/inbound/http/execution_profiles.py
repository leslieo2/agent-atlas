from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.modules.shared.domain.execution import ExecutionBinding, ExecutionProfile


class ExecutionProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: str
    tracing_backend: str = "state"
    execution_binding: ExecutionBinding | None = None

    def to_domain(self) -> tuple[ExecutionProfile, ExecutionBinding | None]:
        executor_config = ExecutionProfile.model_validate(self.model_dump(mode="python"))
        execution_binding = (
            executor_config.execution_binding.model_copy(deep=True)
            if executor_config.execution_binding is not None
            else None
        )
        public_profile = ExecutionProfile(
            backend=executor_config.backend,
            tracing_backend=executor_config.tracing_backend,
        )
        return public_profile, execution_binding
