from __future__ import annotations

import json
from typing import Any

from app.modules.runs.application.ports import TrajectoryStepProjectorPort
from app.modules.runs.domain.models import TrajectoryStep, utc_now
from app.modules.shared.domain.traces import TraceIngestEvent, TraceSpan


class TraceEventTrajectoryProjector(TrajectoryStepProjectorPort):
    def project(
        self,
        event: TraceIngestEvent,
        span: TraceSpan | None = None,
    ) -> TrajectoryStep:
        payload_input = span.input if span is not None else event.input
        payload_output = span.output if span is not None else event.output
        step_id = span.span_id if span is not None else event.span_id
        parent_step_id = span.parent_span_id if span is not None else event.parent_span_id
        run_id = span.run_id if span is not None else event.run_id
        step_type = span.step_type if span is not None else event.step_type
        tool_name = span.tool_name if span is not None else event.tool_name
        latency_ms = span.latency_ms if span is not None else event.latency_ms
        token_usage = span.token_usage if span is not None else event.token_usage
        started_at = span.received_at if span is not None else utc_now()

        return TrajectoryStep(
            id=step_id,
            run_id=run_id,
            step_type=step_type,
            parent_step_id=parent_step_id,
            prompt=self._render_prompt(payload_input),
            output=self._render_output(payload_output),
            model=self._extract_model(payload_input),
            temperature=self._extract_temperature(payload_input),
            latency_ms=latency_ms,
            token_usage=token_usage,
            success=self._extract_success(payload_output),
            tool_name=tool_name,
            started_at=started_at,
        )

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

    def _extract_model(self, payload: dict[str, Any]) -> str | None:
        model = payload.get("model")
        if isinstance(model, str) and model:
            return model
        return None

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
