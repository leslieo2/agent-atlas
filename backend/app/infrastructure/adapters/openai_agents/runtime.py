from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

from pydantic import SecretStr

from app.core.errors import AgentLoadFailedError
from app.execution_plane.contracts import RunnerRunSpec
from app.execution_plane.translation import (
    empty_artifact_manifest,
    producer_for_runtime,
    terminal_result_from_runtime_result,
    trace_event_to_event_envelope,
)
from app.infrastructure.adapters.openai_agents.catalog import PublishedOpenAIAgentLoader
from app.infrastructure.adapters.openai_agents.trace_mapper import (
    build_trace_events_from_agent_run,
)
from app.infrastructure.adapters.runtime import RuntimeAdapter
from app.infrastructure.adapters.runtime_utils import usage_total_tokens
from app.modules.agents.domain.models import AgentBuildContext, PublishedAgent
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RuntimeExecutionResult


class OpenAIAgentsSdkAdapter(RuntimeAdapter):
    _instructions = "You are a concise assistant inside Agent Atlas. Return the best direct answer."

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
            except BaseException as exc:  # pragma: no cover
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
            token_usage=usage_total_tokens(usage),
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
        payload: RunnerRunSpec,
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
            token_usage=usage_total_tokens(usage),
            provider="openai-agents-sdk",
            resolved_model=effective_model,
        )
        producer = producer_for_runtime(
            runtime="openai-agents-sdk",
            framework=published_agent.framework,
        )
        trace_events = build_trace_events_from_agent_run(
            run_id=context.run_id,
            prompt=payload.prompt,
            model=effective_model,
            provider="openai-agents-sdk",
            result=result,
        )
        return PublishedRunExecutionResult(
            runtime_result=runtime_result,
            event_envelopes=[
                trace_event_to_event_envelope(
                    event,
                    experiment_id=payload.experiment_id,
                    attempt=payload.attempt,
                    attempt_id=payload.attempt_id,
                    producer=producer,
                    sequence=index,
                )
                for index, event in enumerate(trace_events, start=1)
            ],
            terminal_result=terminal_result_from_runtime_result(
                payload=payload,
                runtime_result=runtime_result,
                producer=producer,
                tool_calls=sum(1 for event in trace_events if event.step_type.value == "tool"),
            ),
            artifact_manifest=empty_artifact_manifest(payload=payload, producer=producer),
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
    def _published_agent_from_payload(payload: RunnerRunSpec) -> PublishedAgent:
        snapshot = payload.published_agent_snapshot
        try:
            return PublishedAgent.model_validate(snapshot)
        except Exception as exc:
            raise AgentLoadFailedError(
                "run payload is missing a valid published agent snapshot",
                agent_id=payload.agent_id,
            ) from exc
