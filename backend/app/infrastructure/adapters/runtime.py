from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import SecretStr

from app.core.config import RuntimeMode, settings
from app.core.errors import (
    ModelNotFoundError,
    ProviderAuthError,
    ProviderTimeoutError,
    RateLimitedError,
    UnsupportedAdapterError,
)
from app.infrastructure.adapters.framework_registry import FrameworkRegistry
from app.modules.agents.domain.models import AgentBuildContext, adapter_kind_for_framework
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RunSpec, RuntimeExecutionResult
from app.modules.shared.domain.enums import AdapterKind

from .runtime_utils import extract_error_message


class RuntimeAdapter(Protocol):
    def execute(
        self,
        *,
        api_key: SecretStr | None,
        model: str,
        prompt: str,
    ) -> RuntimeExecutionResult: ...


class PublishedAgentRuntimeAdapter(Protocol):
    def execute_published(
        self,
        *,
        api_key: SecretStr | None,
        payload: RunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult: ...


def _iter_exception_chain(exc: BaseException) -> list[BaseException]:
    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        chain.append(current)
        seen.add(id(current))
        next_exc = current.__cause__ or current.__context__
        current = next_exc if isinstance(next_exc, BaseException) else None
    return chain


def _extract_error_code(candidate: BaseException) -> str | None:
    code = getattr(candidate, "code", None)
    if isinstance(code, str) and code.strip():
        return code.strip()

    body = getattr(candidate, "body", None)
    if isinstance(body, dict):
        direct_code = body.get("code")
        if isinstance(direct_code, str) and direct_code.strip():
            return direct_code.strip()
        nested_error = body.get("error")
        if isinstance(nested_error, dict):
            nested_code = nested_error.get("code")
            if isinstance(nested_code, str) and nested_code.strip():
                return nested_code.strip()
    return None


def _extract_error_status(candidate: BaseException) -> int | None:
    status_code = getattr(candidate, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    return None


def _candidate_message(candidate: BaseException) -> str:
    body = getattr(candidate, "body", None)
    body_message = extract_error_message(body)
    if body_message:
        return body_message

    response = getattr(candidate, "response", None)
    response_text = getattr(response, "text", None)
    if isinstance(response_text, str) and response_text.strip():
        return response_text.strip()

    direct_message = str(candidate).strip()
    if direct_message:
        return direct_message

    return ""


def _looks_like_model_not_found(candidate: BaseException) -> bool:
    if isinstance(candidate, ModelNotFoundError):
        return True

    code = _extract_error_code(candidate)
    if code == ModelNotFoundError.code:
        return True

    if _extract_error_status(candidate) == 400 and getattr(candidate, "param", None) == "model":
        message = _candidate_message(candidate).lower()
        if "model" in message and any(
            phrase in message for phrase in ("not found", "does not exist", "unknown", "invalid")
        ):
            return True

    message = _candidate_message(candidate).lower()
    return bool(
        "model_not_found" in message
        or ("model" in message and ("not found" in message or "does not exist" in message))
    )


def _looks_like_provider_auth_error(candidate: BaseException) -> bool:
    if isinstance(candidate, ProviderAuthError):
        return True

    if _extract_error_status(candidate) in {401, 403}:
        return True

    message = _candidate_message(candidate).lower()
    auth_phrases = ("invalid api key", "incorrect api key", "authentication")
    return any(phrase in message for phrase in auth_phrases)


def _looks_like_rate_limited(candidate: BaseException) -> bool:
    if isinstance(candidate, RateLimitedError):
        return True

    if _extract_error_status(candidate) == 429:
        return True

    message = _candidate_message(candidate).lower()
    return "rate limit" in message or "too many requests" in message


def _looks_like_timeout(candidate: BaseException) -> bool:
    if isinstance(candidate, ProviderTimeoutError):
        return True

    message = _candidate_message(candidate).lower()
    return "timed out" in message or "timeout" in message


def _normalize_runtime_exception(exc: Exception, model: str) -> Exception:
    for candidate in _iter_exception_chain(exc):
        if _looks_like_model_not_found(candidate):
            if isinstance(candidate, ModelNotFoundError):
                return candidate
            return ModelNotFoundError(model=model, message=f"model '{model}' not found")

        if _looks_like_provider_auth_error(candidate):
            if isinstance(candidate, ProviderAuthError):
                return candidate
            return ProviderAuthError("provider authentication failed")

        if _looks_like_rate_limited(candidate):
            if isinstance(candidate, RateLimitedError):
                return candidate
            return RateLimitedError("provider rate limit exceeded")

        if _looks_like_timeout(candidate):
            if isinstance(candidate, ProviderTimeoutError):
                return candidate
            return ProviderTimeoutError("provider request timed out")
    return exc


class ModelRuntimeService:
    def __init__(
        self,
        adapters: Mapping[AdapterKind, RuntimeAdapter] | None = None,
        published_adapter: PublishedAgentRuntimeAdapter | None = None,
        framework_registry: FrameworkRegistry | None = None,
    ) -> None:
        self.api_key = settings.openai_api_key
        self.runtime_mode = settings.runtime_mode
        self.adapters = dict(adapters or self._default_adapters())
        self.published_adapter = published_adapter
        self.framework_registry = framework_registry

    def _effective_runtime_mode(self) -> RuntimeMode:
        if self.runtime_mode == RuntimeMode.MOCK:
            return RuntimeMode.MOCK
        if self.runtime_mode == RuntimeMode.LIVE:
            return RuntimeMode.LIVE
        return RuntimeMode.LIVE if self.api_key else RuntimeMode.MOCK

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> RuntimeExecutionResult:
        effective_mode = self._effective_runtime_mode()
        if effective_mode == RuntimeMode.MOCK:
            return self._simulate_output(agent_type, model, prompt)

        try:
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY is not set")
            adapter = self.adapters.get(agent_type)
            if adapter is None:
                raise UnsupportedAdapterError(
                    f"agent_type '{agent_type.value}' is not supported for live execution",
                    agent_type=agent_type.value,
                )
            return adapter.execute(api_key=self.api_key, model=model, prompt=prompt)
        except Exception as exc:
            normalized_exc = _normalize_runtime_exception(exc, model)
            if effective_mode == RuntimeMode.LIVE:
                if normalized_exc is exc:
                    raise
                raise normalized_exc from exc
            fallback = self._simulate_output(agent_type, model, prompt)
            fallback.output = f"{fallback.output} [fallback from live runtime: {normalized_exc}]"
            return fallback

    def execute_published(self, run_id: Any, payload: RunSpec) -> PublishedRunExecutionResult:
        resolved_agent_type = payload.agent_type
        if self.framework_registry is not None:
            published_agent = self.framework_registry.published_agent_from_payload(payload)
            resolved_agent_type = adapter_kind_for_framework(published_agent.framework)

        effective_mode = self._effective_runtime_mode()
        if effective_mode == RuntimeMode.MOCK:
            fallback = self._simulate_output(resolved_agent_type, payload.model, payload.prompt)
            return PublishedRunExecutionResult(
                runtime_result=fallback.model_copy(update={"resolved_model": payload.model})
            )

        try:
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY is not set")
            context = AgentBuildContext(
                run_id=run_id,
                project=payload.project,
                dataset=payload.dataset,
                prompt=payload.prompt,
                tags=payload.tags,
                project_metadata=payload.project_metadata,
            )
            if self.framework_registry is not None:
                return self.framework_registry.execute_published(
                    api_key=self.api_key,
                    payload=payload,
                    context=context,
                )
            if self.published_adapter is None:
                raise RuntimeError("published runtime is not configured")
            return self.published_adapter.execute_published(
                api_key=self.api_key,
                payload=payload,
                context=context,
            )
        except Exception as exc:
            normalized_exc = _normalize_runtime_exception(exc, payload.model)
            if effective_mode == RuntimeMode.LIVE:
                if normalized_exc is exc:
                    raise
                raise normalized_exc from exc
            fallback = self._simulate_output(resolved_agent_type, payload.model, payload.prompt)
            fallback.output = f"{fallback.output} [fallback from live runtime: {normalized_exc}]"
            return PublishedRunExecutionResult(
                runtime_result=fallback.model_copy(update={"resolved_model": payload.model})
            )

    @staticmethod
    def _default_adapters() -> dict[AdapterKind, RuntimeAdapter]:
        from app.infrastructure.adapters.langchain.runtime import LangChainRuntimeAdapter
        from app.infrastructure.adapters.openai_agents.runtime import OpenAIAgentsSdkAdapter

        return {
            AdapterKind.OPENAI_AGENTS: OpenAIAgentsSdkAdapter(),
            AdapterKind.LANGCHAIN: LangChainRuntimeAdapter(),
        }

    def _simulate_output(
        self,
        agent_type: AdapterKind,
        model: str,
        prompt: str,
    ) -> RuntimeExecutionResult:
        return RuntimeExecutionResult(
            output=(
                f"Simulated {agent_type.value} execution for model={model}: "
                f"{prompt[:120] if len(prompt) > 120 else prompt}"
            ),
            latency_ms=25,
            token_usage=0,
            provider="mock",
            resolved_model=model,
        )
