from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from pydantic import SecretStr

from app.core.config import RuntimeMode, settings
from app.core.errors import (
    AgentLoadFailedError,
    ModelNotFoundError,
    ProviderAuthError,
    ProviderTimeoutError,
    RateLimitedError,
    UnsupportedAdapterError,
)
from app.infrastructure.adapters.agents import PublishedOpenAIAgentLoader
from app.modules.agents.domain.models import AgentBuildContext, PublishedAgent
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RunSpec, RuntimeExecutionResult
from app.modules.shared.domain.enums import AdapterKind, StepType
from app.modules.traces.domain.models import TraceIngestEvent


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


def _dump_json(value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def _extract_message_text(item: object) -> str:
    if getattr(item, "type", None) != "message":
        return ""

    fragments: list[str] = []
    for content in getattr(item, "content", []) or []:
        content_type = getattr(content, "type", None)
        if content_type == "output_text":
            text = getattr(content, "text", None)
        elif content_type == "refusal":
            text = getattr(content, "refusal", None)
        else:
            text = None
        if isinstance(text, str) and text.strip():
            fragments.append(text.strip())
    return "\n".join(fragments)


def _serialize_response_output(items: Sequence[object]) -> str:
    serialized: list[object] = []
    for item in items:
        if hasattr(item, "model_dump"):
            serialized.append(item.model_dump(exclude_unset=True))
        else:
            serialized.append(str(item))
    return _dump_json(serialized)


def _tool_outputs_by_call_id(result: object) -> dict[str, str]:
    tool_outputs: dict[str, str] = {}
    for item in getattr(result, "new_items", []) or []:
        raw_item = getattr(item, "raw_item", None)
        if isinstance(raw_item, dict):
            call_id = raw_item.get("call_id")
            fallback_output = raw_item.get("output")
            item_type = raw_item.get("type")
        else:
            call_id = getattr(raw_item, "call_id", None)
            fallback_output = getattr(raw_item, "output", None)
            item_type = getattr(raw_item, "type", None)

        if (
            type(item).__name__ != "ToolCallOutputItem"
            and item_type != "function_call_output"
            and not (call_id and hasattr(item, "output"))
        ):
            continue

        if not isinstance(call_id, str) or not call_id:
            continue

        output = getattr(item, "output", None)
        normalized_output = (
            output if isinstance(output, str) else str(output or fallback_output or "")
        )
        tool_outputs[call_id] = normalized_output
    return tool_outputs


def _build_follow_up_prompt(prompt: str, tool_outputs: Sequence[str]) -> str:
    if not tool_outputs:
        return prompt
    return "\n".join(
        [
            prompt,
            "",
            "Tool outputs:",
            *tool_outputs,
        ]
    )


def build_trace_events_from_agent_run(
    *,
    run_id: Any,
    prompt: str,
    model: str,
    provider: str,
    result: object,
) -> list[TraceIngestEvent]:
    raw_responses = getattr(result, "raw_responses", None)
    if not isinstance(raw_responses, list) or not raw_responses:
        return []

    tool_outputs = _tool_outputs_by_call_id(result)
    events: list[TraceIngestEvent] = []
    previous_parent_span_id: str | None = None
    previous_tool_outputs: list[str] = []
    step_index = 1

    for response in raw_responses:
        response_items = getattr(response, "output", None)
        if not isinstance(response_items, list):
            response_items = []

        llm_prompt = (
            prompt
            if not events
            else _build_follow_up_prompt(prompt=prompt, tool_outputs=previous_tool_outputs)
        )
        llm_span_id = f"span-{run_id}-{step_index}"
        step_index += 1

        tool_calls = [
            item for item in response_items if getattr(item, "type", None) == "function_call"
        ]
        if tool_calls:
            llm_output = "\n".join(
                [
                    "tool_call: "
                    f"{getattr(item, 'name', 'unknown')}({getattr(item, 'arguments', '{}')})"
                    for item in tool_calls
                ]
            )
        else:
            message_outputs = [
                text for text in (_extract_message_text(item) for item in response_items) if text
            ]
            llm_output = (
                message_outputs[-1]
                if message_outputs
                else _serialize_response_output(response_items)
            )

        events.append(
            TraceIngestEvent(
                run_id=run_id,
                span_id=llm_span_id,
                parent_span_id=previous_parent_span_id,
                step_type=StepType.LLM,
                name=model,
                input={
                    "prompt": llm_prompt,
                    "model": model,
                    "temperature": 0.0,
                },
                output={
                    "output": llm_output,
                    "success": True,
                    "provider": provider,
                },
                token_usage=_usage_total_tokens(getattr(response, "usage", None)),
            )
        )

        current_parent_span_id = llm_span_id
        current_tool_outputs: list[str] = []
        for tool_call in tool_calls:
            call_id = getattr(tool_call, "call_id", None)
            tool_name = getattr(tool_call, "name", None)
            arguments = getattr(tool_call, "arguments", None)
            if not isinstance(call_id, str) or not isinstance(tool_name, str):
                continue

            output = tool_outputs.get(call_id)
            if output is None:
                continue

            tool_span_id = f"span-{run_id}-{step_index}"
            step_index += 1
            prompt_payload = arguments if isinstance(arguments, str) else _dump_json(arguments)
            events.append(
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=tool_span_id,
                    parent_span_id=current_parent_span_id,
                    step_type=StepType.TOOL,
                    name=tool_name,
                    input={
                        "prompt": prompt_payload,
                        "tool_name": tool_name,
                    },
                    output={
                        "output": output,
                        "success": True,
                    },
                    tool_name=tool_name,
                )
            )
            current_parent_span_id = tool_span_id
            current_tool_outputs.append(f"{tool_name}: {output}")

        previous_parent_span_id = current_parent_span_id
        previous_tool_outputs = current_tool_outputs

    return events


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
        "You are a concise assistant inside Agent Atlas. " "Return the best direct answer."
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

        runner_thread = threading.Thread(target=runner_target, name="agent-atlas-openai-replay")
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
            name="Agent Atlas Assistant",
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


class PublishedOpenAIAgentAdapter(OpenAIAgentsSdkAdapter):
    def __init__(self, agent_loader: PublishedOpenAIAgentLoader) -> None:
        self.agent_loader = agent_loader

    def execute_published(
        self,
        *,
        api_key: SecretStr | None,
        payload: RunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult:
        try:
            from agents import OpenAIProvider, RunConfig
        except ImportError as exc:
            raise RuntimeError("OpenAI Agents SDK package 'agents' is not installed") from exc

        published_agent = self._published_agent_from_payload(payload)
        agent = self.agent_loader.build_agent(
            published_agent=published_agent,
            context=context,
        )
        run_config = RunConfig(
            model=published_agent.default_model,
            model_provider=OpenAIProvider(
                api_key=api_key.get_secret_value() if api_key is not None else None,
            ),
            workflow_name=published_agent.name,
            group_id=str(payload.project),
            trace_metadata={
                "run_id": str(context.run_id),
                "agent_id": payload.agent_id,
                "framework": published_agent.framework,
            },
        )
        started = time.perf_counter()
        result = self._run_with_explicit_event_loop(agent, payload.prompt, run_config, context)
        latency_ms = int((time.perf_counter() - started) * 1000)
        final_output = getattr(result, "final_output", "")
        context_wrapper = getattr(result, "context_wrapper", None)
        usage = getattr(context_wrapper, "usage", None)
        resolved_model = self._resolve_model(result=result, agent=agent, run_config=run_config)
        effective_model = resolved_model or published_agent.default_model
        runtime_result = RuntimeExecutionResult(
            output=final_output if isinstance(final_output, str) else str(final_output),
            latency_ms=latency_ms,
            token_usage=_usage_total_tokens(usage),
            provider="openai-agents-sdk",
            resolved_model=effective_model,
        )
        return PublishedRunExecutionResult(
            runtime_result=runtime_result,
            trace_events=build_trace_events_from_agent_run(
                run_id=context.run_id,
                prompt=payload.prompt,
                model=effective_model,
                provider="openai-agents-sdk",
                result=result,
            ),
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

    @staticmethod
    def _published_agent_from_payload(payload: RunSpec) -> PublishedAgent:
        snapshot = payload.project_metadata.get("agent_snapshot")
        try:
            return PublishedAgent.model_validate(snapshot)
        except Exception as exc:
            raise AgentLoadFailedError(
                "run payload is missing a valid published agent snapshot",
                agent_id=payload.agent_id,
            ) from exc


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
        published_adapter: PublishedOpenAIAgentAdapter | None = None,
    ) -> None:
        self.api_key = settings.openai_api_key
        self.runtime_mode = settings.runtime_mode
        self.adapters = dict(adapters or self._default_adapters())
        self.published_adapter = published_adapter

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
        effective_mode = self._effective_runtime_mode()
        if effective_mode == RuntimeMode.MOCK:
            fallback = self._simulate_output(payload.agent_type, payload.model, payload.prompt)
            return PublishedRunExecutionResult(
                runtime_result=fallback.model_copy(update={"resolved_model": payload.model})
            )

        try:
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY is not set")
            if self.published_adapter is None:
                raise RuntimeError("published runtime is not configured")
            context = AgentBuildContext(
                run_id=run_id,
                project=payload.project,
                dataset=payload.dataset,
                prompt=payload.prompt,
                tags=payload.tags,
                project_metadata=payload.project_metadata,
            )
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
            fallback = self._simulate_output(payload.agent_type, payload.model, payload.prompt)
            fallback.output = f"{fallback.output} [fallback from live runtime: {normalized_exc}]"
            return PublishedRunExecutionResult(
                runtime_result=fallback.model_copy(update={"resolved_model": payload.model})
            )

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
