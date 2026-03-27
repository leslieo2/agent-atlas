from __future__ import annotations

import time
from typing import Any

from pydantic import SecretStr

from app.core.errors import AgentLoadFailedError
from app.infrastructure.adapters.langchain.catalog import PublishedLangChainAgentLoader
from app.infrastructure.adapters.langchain.trace_mapper import (
    build_trace_events_from_langgraph_run,
)
from app.infrastructure.adapters.runtime import RuntimeAdapter
from app.infrastructure.adapters.runtime_utils import usage_total_tokens
from app.modules.agents.domain.models import AgentBuildContext, PublishedAgent
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RunSpec, RuntimeExecutionResult


class LangChainRuntimeAdapter(RuntimeAdapter):
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
            token_usage=usage_total_tokens(usage),
            provider="langchain",
        )


class PublishedLangChainAgentAdapter:
    def __init__(self, agent_loader: PublishedLangChainAgentLoader) -> None:
        self.agent_loader = agent_loader

    def execute_published(
        self,
        *,
        api_key: SecretStr | None,
        payload: RunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult:
        del api_key

        published_agent = self._published_agent_from_payload(payload)
        agent = self.agent_loader.build_agent(
            published_agent=published_agent,
            context=context,
        )
        started = time.perf_counter()
        result = self._invoke_runnable(
            agent=agent,
            prompt=payload.prompt,
            context=context,
            agent_id=payload.agent_id,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        output = self._stringify_output(result)
        token_usage = self._extract_token_usage(result)
        runtime_result = RuntimeExecutionResult(
            output=output,
            latency_ms=latency_ms,
            token_usage=token_usage,
            provider="langchain",
            execution_backend="langgraph",
            resolved_model=published_agent.default_model,
        )
        return PublishedRunExecutionResult(
            runtime_result=runtime_result,
            trace_events=build_trace_events_from_langgraph_run(
                run_id=context.run_id,
                prompt=payload.prompt,
                model=published_agent.default_model,
                provider="langchain",
                result=result,
                token_usage=token_usage,
                latency_ms=latency_ms,
            ),
        )

    def _invoke_runnable(
        self,
        *,
        agent: Any,
        prompt: str,
        context: AgentBuildContext,
        agent_id: str,
    ) -> Any:
        invoke = getattr(agent, "invoke", None)
        if callable(invoke):
            for candidate in self._candidate_inputs(prompt=prompt, context=context):
                try:
                    return invoke(candidate)
                except TypeError:
                    continue
            return invoke(prompt)

        if callable(agent):
            for args in ((prompt, context), (prompt,)):
                try:
                    return agent(*args)
                except TypeError:
                    continue

        raise AgentLoadFailedError(
            "langchain published agent is not invokable",
            agent_id=agent_id,
        )

    @staticmethod
    def _candidate_inputs(*, prompt: str, context: AgentBuildContext) -> list[Any]:
        try:
            from langchain_core.messages import HumanMessage
        except ImportError:
            return [
                {"input": prompt, "prompt": prompt, "context": context},
                prompt,
            ]

        return [
            {
                "messages": [HumanMessage(content=prompt)],
                "input": prompt,
                "prompt": prompt,
                "context": context,
            },
            {"input": prompt, "prompt": prompt, "context": context},
            prompt,
        ]

    @staticmethod
    def _stringify_output(result: Any) -> str:
        if isinstance(result, str):
            return result
        content = getattr(result, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(result, dict):
            for key in ("output", "final_output", "answer", "response"):
                candidate = result.get(key)
                if isinstance(candidate, str):
                    return candidate
            messages = result.get("messages")
            if isinstance(messages, list) and messages:
                return PublishedLangChainAgentAdapter._stringify_output(messages[-1])
        return str(result)

    @staticmethod
    def _extract_token_usage(result: Any) -> int:
        if isinstance(result, dict):
            usage = result.get("usage_metadata") or result.get("usage")
            if usage is not None:
                return usage_total_tokens(usage)
            messages = result.get("messages")
            if isinstance(messages, list) and messages:
                return PublishedLangChainAgentAdapter._extract_token_usage(messages[-1])

        usage = getattr(result, "usage_metadata", None) or getattr(result, "usage", None)
        return usage_total_tokens(usage)

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
