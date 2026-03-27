from __future__ import annotations


class AppError(Exception):
    code = "app_error"
    status_code = 400

    def __init__(self, message: str, **context: str) -> None:
        self.message = message
        self.context = {key: value for key, value in context.items() if value}
        super().__init__(self.message)

    def to_detail(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            **self.context,
        }


class ModelNotFoundError(AppError, ValueError):
    code = "model_not_found"
    status_code = 400

    def __init__(self, model: str, message: str | None = None) -> None:
        self.model = model
        super().__init__(message or f"model '{model}' not found", model=model)


class ProviderAuthError(AppError):
    code = "provider_auth_error"
    status_code = 502


class RateLimitedError(AppError):
    code = "rate_limited"
    status_code = 429


class ProviderTimeoutError(AppError):
    code = "provider_timeout"
    status_code = 504


class UnsupportedAdapterError(AppError, ValueError):
    code = "unsupported_adapter"
    status_code = 400


class AgentNotPublishedError(AppError, ValueError):
    code = "agent_not_published"
    status_code = 400

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"agent_id '{agent_id}' is not published", agent_id=agent_id)


class AgentValidationFailedError(AppError, ValueError):
    code = "agent_validation_failed"
    status_code = 400

    def __init__(self, agent_id: str, message: str | None = None) -> None:
        self.agent_id = agent_id
        super().__init__(
            message or f"agent_id '{agent_id}' failed contract validation",
            agent_id=agent_id,
        )


class AgentLoadFailedError(AppError):
    code = "agent_load_failed"
    status_code = 500


class UnsupportedOperationError(AppError, ValueError):
    code = "unsupported_operation"
    status_code = 400


class DatasetNotFoundError(AppError, ValueError):
    code = "dataset_not_found"
    status_code = 404

    def __init__(self, dataset: str) -> None:
        self.dataset = dataset
        super().__init__(f"dataset '{dataset}' was not found", dataset=dataset)
