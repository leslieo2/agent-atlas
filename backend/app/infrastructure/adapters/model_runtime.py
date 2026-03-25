from __future__ import annotations

import asyncio
import os
import threading
import time
from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import SecretStr

from app.core.config import settings
from app.core.errors import ModelNotFoundError
from app.modules.runs.domain.models import RuntimeExecutionResult
from app.modules.shared.domain.enums import AdapterKind


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


def _looks_like_model_not_found(candidate: BaseException) -> bool:
    if isinstance(candidate, ModelNotFoundError):
        return True

    code = _extract_error_code(candidate)
    if code == ModelNotFoundError.code:
        return True

    message = str(candidate).lower()
    return bool(
        "model_not_found" in message
        or ("model" in message and ("not found" in message or "does not exist" in message))
    )


def _normalize_runtime_exception(exc: Exception, model: str) -> Exception:
    for candidate in _iter_exception_chain(exc):
        if not _looks_like_model_not_found(candidate):
            continue

        if isinstance(candidate, ModelNotFoundError):
            return candidate

        return ModelNotFoundError(model=model, message=f"model '{model}' not found")
    return exc


class OpenAIAgentsSdkAdapter:
    _instructions = (
        "You are a concise assistant inside Agent Flight Recorder. "
        "Return the best direct answer."
    )

    async def _run_async(self, agent: Any, prompt: str) -> object:
        from agents import Runner

        return await Runner.run(agent, prompt)

    def _run_with_explicit_event_loop(self, agent: Any, prompt: str) -> object:
        from agents import Runner

        if not hasattr(Runner, "run"):
            return Runner.run_sync(agent, prompt)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._run_async(agent, prompt))

        result: object | None = None
        error: BaseException | None = None

        def runner_target() -> None:
            nonlocal result, error
            try:
                result = asyncio.run(self._run_async(agent, prompt))
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
            from agents import Agent
        except ImportError as exc:
            raise RuntimeError("OpenAI Agents SDK package 'agents' is not installed") from exc

        resolved_api_key = api_key.get_secret_value() if api_key is not None else None
        previous_api_key = os.environ.get("OPENAI_API_KEY")
        if resolved_api_key:
            os.environ["OPENAI_API_KEY"] = resolved_api_key

        agent = Agent(
            name="Agent Flight Recorder Assistant",
            instructions=self._instructions,
            model=model,
        )
        try:
            started = time.perf_counter()
            result = self._run_with_explicit_event_loop(agent, prompt)
        finally:
            if resolved_api_key:
                if previous_api_key is None:
                    os.environ.pop("OPENAI_API_KEY", None)
                else:
                    os.environ["OPENAI_API_KEY"] = previous_api_key
        latency_ms = int((time.perf_counter() - started) * 1000)
        final_output = getattr(result, "final_output", "")
        context_wrapper = getattr(result, "context_wrapper", None)
        usage = getattr(context_wrapper, "usage", None)
        return RuntimeExecutionResult(
            output=final_output if isinstance(final_output, str) else str(final_output),
            latency_ms=latency_ms,
            token_usage=_usage_total_tokens(usage),
            provider="openai-agents-sdk",
        )


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
    def __init__(self, adapters: Mapping[AdapterKind, RuntimeAdapter] | None = None) -> None:
        raw_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AFLIGHT_OPENAI_API_KEY")
        self.api_key = SecretStr(raw_api_key) if raw_api_key else None
        self.runtime_mode = (settings.runtime_mode or "auto").lower()
        if self.runtime_mode not in {"auto", "live", "mock"}:
            self.runtime_mode = "auto"
        self.adapters = dict(adapters or self._default_adapters())

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> RuntimeExecutionResult:
        if not self.api_key:
            if self.runtime_mode == "live":
                raise RuntimeError("OPENAI_API_KEY is not set")
            return self._simulate_output(agent_type, model, prompt)

        if self.runtime_mode == "mock":
            return self._simulate_output(agent_type, model, prompt)

        try:
            adapter = self.adapters.get(agent_type)
            if adapter is None:
                raise RuntimeError(
                    f"agent_type '{agent_type.value}' is not supported for live execution"
                )
            return adapter.execute(api_key=self.api_key, model=model, prompt=prompt)
        except Exception as exc:
            normalized_exc = _normalize_runtime_exception(exc, model)
            if self.runtime_mode == "live":
                if normalized_exc is exc:
                    raise
                raise normalized_exc from exc
            fallback = self._simulate_output(agent_type, model, prompt)
            fallback.output = f"{fallback.output} [fallback from live runtime: {normalized_exc}]"
            return fallback

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
        )


model_runtime_service = ModelRuntimeService()
