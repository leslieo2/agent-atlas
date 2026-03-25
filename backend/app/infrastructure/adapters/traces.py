from __future__ import annotations

import json
from typing import Any

from app.modules.runs.domain.models import TrajectoryStep
from app.modules.traces.domain.models import TraceIngestEvent, TraceSpan


class DefaultTraceProjector:
    def project(self, event: TraceIngestEvent) -> TraceSpan:
        return TraceSpan(
            run_id=event.run_id,
            span_id=event.span_id,
            parent_span_id=event.parent_span_id,
            step_type=event.step_type,
            input=event.input,
            output=event.output,
            tool_name=event.tool_name,
            latency_ms=event.latency_ms,
            token_usage=event.token_usage,
            image_digest=event.image_digest,
            prompt_version=event.prompt_version,
        )

    def project_step(self, event: TraceIngestEvent, span: TraceSpan) -> TrajectoryStep:
        return TrajectoryStep(
            id=span.span_id,
            run_id=span.run_id,
            step_type=span.step_type,
            parent_step_id=span.parent_span_id,
            prompt=self._render_prompt(span.input),
            output=self._render_output(span.output),
            model=self._extract_model(event, span.input),
            temperature=self._extract_temperature(span.input),
            latency_ms=span.latency_ms,
            token_usage=span.token_usage,
            success=self._extract_success(span.output),
            tool_name=span.tool_name,
            started_at=span.received_at,
        )

    def normalize(
        self,
        span: TraceSpan,
        event: TraceIngestEvent | None = None,
    ) -> dict[str, Any]:
        return {
            "run_id": str(span.run_id),
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
            "step_type": span.step_type.value,
            "input": span.input,
            "output": span.output,
            "tool_name": span.tool_name,
            "latency_ms": span.latency_ms,
            "token_usage": span.token_usage,
            "image_digest": span.image_digest,
            "prompt_version": span.prompt_version,
            "received_at": span.received_at.isoformat(),
        }

    def _render_prompt(self, payload: dict[str, Any]) -> str:
        prompt = payload.get("prompt")
        if isinstance(prompt, str) and prompt:
            return prompt
        return self._serialize_payload(payload)

    def _render_output(self, payload: dict[str, Any]) -> str:
        output = payload.get("output")
        if isinstance(output, str) and output:
            return output
        return self._serialize_payload(payload)

    def _extract_model(self, event: TraceIngestEvent, payload: dict[str, Any]) -> str:
        model = payload.get("model")
        if isinstance(model, str) and model:
            return model
        return event.name

    def _extract_temperature(self, payload: dict[str, Any]) -> float:
        temperature = payload.get("temperature", 0.0)
        if isinstance(temperature, int | float):
            return float(temperature)
        return 0.0

    def _extract_success(self, payload: dict[str, Any]) -> bool:
        success = payload.get("success")
        if isinstance(success, bool):
            return success
        return "error" not in payload

    def _serialize_payload(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
