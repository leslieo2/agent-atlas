from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module
from importlib.metadata import entry_points
from typing import Any, Protocol, cast

from agent_atlas_contracts.execution import RunnerRunSpec
from agent_atlas_contracts.runtime import AgentBuildContext
from pydantic import SecretStr

from app.core.config import settings
from app.core.errors import (
    ModelNotFoundError,
    ProviderAuthError,
    ProviderTimeoutError,
    RateLimitedError,
    UnsupportedAdapterError,
)
from app.execution.application.results import (
    PublishedRunExecutionResult,
    RuntimeExecutionResult,
)
from app.modules.agents.application.ports import PublishedAgentExecutionPort
from app.modules.agents.domain.models import adapter_kind_for_agent_family
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
        payload: RunnerRunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult: ...


class RuntimeAdapterPlugin(Protocol):
    @property
    def adapter_kind(self) -> str: ...

    @property
    def live_adapter(self) -> RuntimeAdapter: ...


RUNTIME_ADAPTER_ENTRY_POINT_GROUP = "agent_atlas.runtime_adapters"
BUILTIN_RUNTIME_PLUGIN_MODULES = (
    "agent_atlas_runner_openai_agents.runtime_plugins",
    "agent_atlas_runner_langgraph.runtime_plugins",
)


def _load_runtime_adapter_builder(plugin_entry: object) -> object | None:
    try:
        builder = cast(Any, plugin_entry).load()
    except Exception:
        return None
    return cast(object, builder)


def _import_runtime_plugin_module(module_name: str) -> object | None:
    try:
        return import_module(module_name)
    except Exception:
        return None


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
        published_execution_dispatcher: PublishedAgentExecutionPort | None = None,
        *,
        simulate_outputs: bool = False,
    ) -> None:
        self.api_key = settings.openai_api_key
        self.adapters = dict(adapters or self._default_adapters())
        self.published_adapter = published_adapter
        self.published_execution_dispatcher = published_execution_dispatcher
        self.simulate_outputs = simulate_outputs

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> RuntimeExecutionResult:
        if self.simulate_outputs:
            return self._simulate_output(agent_type, model, prompt)

        try:
            adapter = self.adapters.get(agent_type)
            if adapter is None:
                raise UnsupportedAdapterError(
                    f"agent_type '{agent_type.value}' is not supported for live execution",
                    agent_type=agent_type.value,
                )
            return adapter.execute(api_key=self.api_key, model=model, prompt=prompt)
        except Exception as exc:
            normalized_exc = _normalize_runtime_exception(exc, model)
            if normalized_exc is exc:
                raise
            raise normalized_exc from exc

    def execute_published(self, run_id: Any, payload: RunnerRunSpec) -> PublishedRunExecutionResult:
        resolved_agent_type = AdapterKind(payload.agent_type)
        if self.published_execution_dispatcher is not None:
            published_agent = self.published_execution_dispatcher.published_agent_from_payload(
                payload
            )
            resolved_agent_type = adapter_kind_for_agent_family(published_agent.agent_family)

        if self.simulate_outputs:
            fallback = self._simulate_output(resolved_agent_type, payload.model, payload.prompt)
            return PublishedRunExecutionResult(
                runtime_result=fallback.model_copy(update={"resolved_model": payload.model})
            )

        try:
            context = AgentBuildContext(
                run_id=run_id,
                project=payload.project,
                dataset=payload.dataset,
                prompt=payload.prompt,
                tags=payload.tags,
                project_metadata=payload.project_metadata,
            )
            if self.published_execution_dispatcher is not None:
                return self.published_execution_dispatcher.execute_published(
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
            if normalized_exc is exc:
                raise
            raise normalized_exc from exc

    @staticmethod
    def _default_adapters() -> dict[AdapterKind, RuntimeAdapter]:
        adapters: dict[AdapterKind, RuntimeAdapter] = {}
        for plugin_entry in entry_points().select(group=RUNTIME_ADAPTER_ENTRY_POINT_GROUP):
            builder = _load_runtime_adapter_builder(plugin_entry)
            if builder is None:
                continue
            _register_runtime_adapter(adapters, builder)

        for module_name in BUILTIN_RUNTIME_PLUGIN_MODULES:
            module = _import_runtime_plugin_module(module_name)
            if module is None:
                continue
            _register_runtime_adapter(
                adapters,
                getattr(module, "build_runtime_adapter_plugin", None),
            )

        return adapters

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


def _register_runtime_adapter(
    adapters: dict[AdapterKind, RuntimeAdapter],
    builder: object,
) -> None:
    if not callable(builder):
        return

    try:
        plugin = builder()
    except Exception:
        return

    adapter_kind = getattr(plugin, "adapter_kind", None)
    live_adapter = _runtime_adapter_plugin_instance(plugin)
    if not isinstance(adapter_kind, str) or live_adapter is None:
        return

    try:
        adapters.setdefault(AdapterKind(adapter_kind), live_adapter)
    except ValueError:
        return


def _runtime_adapter_plugin_instance(plugin: object) -> RuntimeAdapter | None:
    candidate = getattr(plugin, "live_adapter", None)
    if candidate is None or not callable(getattr(candidate, "execute", None)):
        return None
    return cast(RuntimeAdapter, candidate)
