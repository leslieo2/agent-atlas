from __future__ import annotations

import time

from pydantic import SecretStr

from app.infrastructure.adapters.runtime import RuntimeAdapter
from app.infrastructure.adapters.runtime_utils import usage_total_tokens
from app.modules.runs.domain.models import RuntimeExecutionResult


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
