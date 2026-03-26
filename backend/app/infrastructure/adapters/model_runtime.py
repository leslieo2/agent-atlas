from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from pydantic import SecretStr

from app.core.config import RuntimeMode, settings
from app.core.errors import (
    AgentNotRegisteredError,
    ModelNotFoundError,
    ProviderAuthError,
    ProviderTimeoutError,
    RateLimitedError,
    UnsupportedAdapterError,
)
from app.infrastructure.repositories.agents import StateAgentCatalog
from app.modules.runs.domain.models import RunSpec, RuntimeExecutionResult
from app.modules.shared.domain.enums import AdapterKind
from app.registered_agents.context import RegisteredAgentBuildContext


class RuntimeAdapter(Protocol):
    def execute(
        self,
        *,
        api_key: SecretStr | None,
        model: str,
        prompt: str,
    ) -> RuntimeExecutionResult: ...


def _usage_total_tokens(usage: object) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get("total_tokens", 0) or 0)
    return int(getattr(usage, "total_tokens", 0) or 0)


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


def _iter_mapping_values(value: object) -> Sequence[object]:
    if isinstance(value, Mapping):
        return list(value.values())
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return list(value)
    return []


def _extract_error_message(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("message", "detail", "error_description"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for nested in _iter_mapping_values(value):
            message = _extract_error_message(nested)
            if message:
                return message
        return ""
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for item in value:
            message = _extract_error_message(item)
            if message:
                return message
    return ""


def _candidate_message(candidate: BaseException) -> str:
    body = getattr(candidate, "body", None)
    body_message = _extract_error_message(body)
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


class OpenAIAgentsSdkAdapter:
    _instructions = (
        "You are a concise assistant inside Agent Flight Recorder. "
        "Return the best direct answer."
    )

    async def _run_async(
        self,
        agent: Any,
        prompt: str,
        run_config: Any,
        context: object | None = None,
    ) -> object:
        from agents import Runner

        return await Runner.run(agent, prompt, context=context, run_config=run_config)

    def _run_with_explicit_event_loop(
        self,
        agent: Any,
        prompt: str,
        run_config: Any,
        context: object | None = None,
    ) -> object:
        from agents import Runner

        if not hasattr(Runner, "run"):
            if context is None:
                return Runner.run_sync(agent, prompt, run_config=run_config)
            try:
                return Runner.run_sync(agent, prompt, context=context, run_config=run_config)
            except TypeError:
                return Runner.run_sync(agent, prompt, run_config=run_config)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._run_async(agent, prompt, run_config, context))

        result: object | None = None
        error: BaseException | None = None

        def runner_target() -> None:
            nonlocal result, error
            try:
                result = asyncio.run(self._run_async(agent, prompt, run_config, context))
            except BaseException as exc:  # pragma: no cover - defensive handoff
                error = exc

        runner_thread = threading.Thread(target=runner_target, name="aflight-openai-replay")
        runner_thread.start()
        runner_thread.join()

        if error is not None:
            raise error
        return result

    def execute(
        self,
        *,
        api_key: SecretStr | None,
        model: str,
        prompt: str,
    ) -> RuntimeExecutionResult:
        try:
            from agents import Agent, OpenAIProvider, RunConfig
        except ImportError as exc:
            raise RuntimeError("OpenAI Agents SDK package 'agents' is not installed") from exc

        agent = Agent(
            name="Agent Flight Recorder Assistant",
            instructions=self._instructions,
            model=model,
        )
        run_config = RunConfig(
            model_provider=OpenAIProvider(
                api_key=api_key.get_secret_value() if api_key is not None else None,
            )
        )
        started = time.perf_counter()
        result = self._run_with_explicit_event_loop(agent, prompt, run_config)
        latency_ms = int((time.perf_counter() - started) * 1000)
        final_output = getattr(result, "final_output", "")
        context_wrapper = getattr(result, "context_wrapper", None)
        usage = getattr(context_wrapper, "usage", None)
        return RuntimeExecutionResult(
            output=final_output if isinstance(final_output, str) else str(final_output),
            latency_ms=latency_ms,
            token_usage=_usage_total_tokens(usage),
            provider="openai-agents-sdk",
            resolved_model=model,
        )


class RegisteredOpenAIAgentAdapter(OpenAIAgentsSdkAdapter):
    def __init__(self, agent_catalog: StateAgentCatalog) -> None:
        self.agent_catalog = agent_catalog

    def execute_registered(
        self,
        *,
        api_key: SecretStr | None,
        payload: RunSpec,
        context: RegisteredAgentBuildContext,
    ) -> RuntimeExecutionResult:
        try:
            from agents import OpenAIProvider, RunConfig
        except ImportError as exc:
            raise RuntimeError("OpenAI Agents SDK package 'agents' is not installed") from exc

        descriptor = self.agent_catalog.get_agent(payload.agent_id)
        if descriptor is None:
            raise AgentNotRegisteredError(payload.agent_id)

        agent = self.agent_catalog.build_agent(payload.agent_id, context=context)
        run_config = RunConfig(
            model=descriptor.default_model,
            model_provider=OpenAIProvider(
                api_key=api_key.get_secret_value() if api_key is not None else None,
            ),
            workflow_name=descriptor.name,
            group_id=str(payload.project),
            trace_metadata={
                "run_id": str(context.run_id),
                "agent_id": payload.agent_id,
                "framework": descriptor.framework,
            },
        )
        started = time.perf_counter()
        result = self._run_with_explicit_event_loop(agent, payload.prompt, run_config, context)
        latency_ms = int((time.perf_counter() - started) * 1000)
        final_output = getattr(result, "final_output", "")
        context_wrapper = getattr(result, "context_wrapper", None)
        usage = getattr(context_wrapper, "usage", None)
        resolved_model = self._resolve_model(result=result, agent=agent, run_config=run_config)
        return RuntimeExecutionResult(
            output=final_output if isinstance(final_output, str) else str(final_output),
            latency_ms=latency_ms,
            token_usage=_usage_total_tokens(usage),
            provider="openai-agents-sdk",
            resolved_model=resolved_model or descriptor.default_model,
        )

    @staticmethod
    def _resolve_model(*, result: object, agent: object, run_config: object) -> str | None:
        for candidate in (
            getattr(getattr(result, "last_agent", None), "model", None),
            getattr(agent, "model", None),
            getattr(run_config, "model", None),
        ):
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return None


class LangChainRuntimeAdapter:
    def execute(
        self,
        *,
        api_key: SecretStr | None,
        model: str,
        prompt: str,
    ) -> RuntimeExecutionResult:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model=model, api_key=api_key)
        started = time.perf_counter()
        response = llm.invoke(prompt)
        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = getattr(response, "usage_metadata", None) or {}
        return RuntimeExecutionResult(
            output=response.content if isinstance(response.content, str) else str(response.content),
            latency_ms=latency_ms,
            token_usage=_usage_total_tokens(usage),
            provider="langchain",
        )


class ModelRuntimeService:
    def __init__(
        self,
        adapters: Mapping[AdapterKind, RuntimeAdapter] | None = None,
        registered_adapter: RegisteredOpenAIAgentAdapter | None = None,
    ) -> None:
        self.api_key = settings.openai_api_key
        self.runtime_mode = settings.runtime_mode
        self.adapters = dict(adapters or self._default_adapters())
        self.registered_adapter = registered_adapter

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

    def execute_registered(self, run_id: Any, payload: RunSpec) -> RuntimeExecutionResult:
        effective_mode = self._effective_runtime_mode()
        if effective_mode == RuntimeMode.MOCK:
            fallback = self._simulate_output(payload.agent_type, payload.model, payload.prompt)
            return fallback.model_copy(update={"resolved_model": payload.model})

        try:
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY is not set")
            if self.registered_adapter is None:
                raise RuntimeError("registered runtime is not configured")
            context = RegisteredAgentBuildContext(
                run_id=run_id,
                project=payload.project,
                dataset=payload.dataset,
                prompt=payload.prompt,
                tags=payload.tags,
                project_metadata=payload.project_metadata,
            )
            return self.registered_adapter.execute_registered(
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
            fallback = self._simulate_output(payload.agent_type, payload.model, payload.prompt)
            fallback.output = f"{fallback.output} [fallback from live runtime: {normalized_exc}]"
            return fallback.model_copy(update={"resolved_model": payload.model})

    @staticmethod
    def _default_adapters() -> dict[AdapterKind, RuntimeAdapter]:
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
