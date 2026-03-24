from __future__ import annotations

import os
import time
from typing import Any

from app.core.config import settings
from app.models.schemas import AdapterKind


class ModelRuntimeService:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AFLIGHT_OPENAI_API_KEY")
        self.runtime_mode = (settings.runtime_mode or "auto").lower()
        if self.runtime_mode not in {"auto", "live", "mock"}:
            self.runtime_mode = "auto"

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            if self.runtime_mode == "live":
                raise RuntimeError("OPENAI_API_KEY is not set")
            return self._simulate_output(agent_type, model, prompt)

        if self.runtime_mode == "mock":
            return self._simulate_output(agent_type, model, prompt)

        try:
            if agent_type == AdapterKind.OPENAI_AGENTS:
                return self._invoke_openai(model, prompt)
            if agent_type == AdapterKind.LANGCHAIN:
                return self._invoke_langchain(model, prompt)
        except Exception as exc:
            if self.runtime_mode == "live":
                raise
            fallback = self._simulate_output(agent_type, model, prompt)
            fallback["output"] = f"{fallback['output']} [fallback from live runtime: {exc}]"
            return fallback

        raise RuntimeError(f"agent_type '{agent_type.value}' is not supported for live execution")

    def _invoke_openai(self, model: str, prompt: str) -> dict[str, Any]:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        started = time.perf_counter()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise assistant inside Agent Flight Recorder."
                        " Return the best direct answer."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        message = response.choices[0].message
        usage = response.usage
        return {
            "output": message.content or "",
            "latency_ms": latency_ms,
            "token_usage": int(getattr(usage, "total_tokens", 0) or 0),
            "provider": "openai",
        }

    def _invoke_langchain(self, model: str, prompt: str) -> dict[str, Any]:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model=model, api_key=self.api_key)
        started = time.perf_counter()
        response = llm.invoke(prompt)
        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = getattr(response, "usage_metadata", None) or {}
        if not isinstance(usage, dict):
            usage = {}
        return {
            "output": (
                response.content if isinstance(response.content, str) else str(response.content)
            ),
            "latency_ms": latency_ms,
            "token_usage": int(usage.get("total_tokens", 0) or 0),
            "provider": "langchain",
        }

    def _simulate_output(self, agent_type: AdapterKind, model: str, prompt: str) -> dict[str, Any]:
        return {
            "output": (
                f"Simulated {agent_type.value} execution for model={model}: "
                f"{prompt[:120] if len(prompt) > 120 else prompt}"
            ),
            "latency_ms": 25,
            "token_usage": 0,
            "provider": "mock",
        }


model_runtime_service = ModelRuntimeService()
