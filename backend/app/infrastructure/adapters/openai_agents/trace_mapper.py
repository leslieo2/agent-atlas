from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.infrastructure.adapters.runtime_utils import extract_error_message, usage_total_tokens
from app.modules.shared.domain.enums import StepType
from app.modules.traces.domain.models import TraceIngestEvent


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


@dataclass(frozen=True)
class ToolCallResult:
    output: str
    success: bool
    error_message: str | None = None


def _mapping_value(candidate: object, key: str) -> object | None:
    if isinstance(candidate, Mapping):
        return candidate.get(key)
    return getattr(candidate, key, None)


def _extract_tool_output_error(raw_item: object, item: object, output: str) -> str | None:
    for candidate in (item, raw_item):
        is_error = _mapping_value(candidate, "is_error")
        if isinstance(is_error, bool) and is_error:
            message = extract_error_message(_mapping_value(candidate, "error"))
            if message:
                return message
            message = extract_error_message(_mapping_value(candidate, "error_message"))
            if message:
                return message
            return output

        status = _mapping_value(candidate, "status")
        if isinstance(status, str) and status.lower() in {"error", "failed"}:
            message = extract_error_message(_mapping_value(candidate, "error"))
            return message or output

    normalized_output = output.strip()
    if not normalized_output:
        return None
    if normalized_output.startswith("An error occurred while running the tool."):
        _, _, detail = normalized_output.partition("Error:")
        return detail.strip() or normalized_output
    return None


def _tool_outputs_by_call_id(result: object) -> dict[str, ToolCallResult]:
    tool_outputs: dict[str, ToolCallResult] = {}
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
        error_message = _extract_tool_output_error(raw_item, item, normalized_output)
        tool_outputs[call_id] = ToolCallResult(
            output=normalized_output,
            success=error_message is None,
            error_message=error_message,
        )
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
    previous_tool_failures: list[str] = []
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

        llm_output_payload: dict[str, object] = {
            "output": llm_output,
            "success": not previous_tool_failures,
            "provider": provider,
        }
        if previous_tool_failures:
            llm_output_payload["error"] = "; ".join(previous_tool_failures)

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
                output=llm_output_payload,
                token_usage=usage_total_tokens(getattr(response, "usage", None)),
            )
        )

        current_parent_span_id = llm_span_id
        current_tool_outputs: list[str] = []
        current_tool_failures: list[str] = []
        for tool_call in tool_calls:
            call_id = getattr(tool_call, "call_id", None)
            tool_name = getattr(tool_call, "name", None)
            arguments = getattr(tool_call, "arguments", None)
            if not isinstance(call_id, str) or not isinstance(tool_name, str):
                continue

            tool_result = tool_outputs.get(call_id)
            if tool_result is None:
                continue

            tool_span_id = f"span-{run_id}-{step_index}"
            step_index += 1
            prompt_payload = arguments if isinstance(arguments, str) else _dump_json(arguments)
            tool_output_payload: dict[str, object] = {
                "output": tool_result.output,
                "success": tool_result.success,
            }
            if tool_result.error_message:
                tool_output_payload["error"] = tool_result.error_message
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
                    output=tool_output_payload,
                    tool_name=tool_name,
                )
            )
            current_parent_span_id = tool_span_id
            current_tool_outputs.append(f"{tool_name}: {tool_result.output}")
            if tool_result.error_message:
                current_tool_failures.append(tool_result.error_message)

        previous_parent_span_id = current_parent_span_id
        previous_tool_outputs = current_tool_outputs
        previous_tool_failures = current_tool_failures

    return events
