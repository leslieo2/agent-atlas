from __future__ import annotations

from collections.abc import Mapping, Sequence


def usage_total_tokens(usage: object) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get("total_tokens", 0) or 0)
    return int(getattr(usage, "total_tokens", 0) or 0)


def _iter_mapping_values(value: object) -> Sequence[object]:
    if isinstance(value, Mapping):
        return list(value.values())
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return list(value)
    return []


def extract_error_message(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("message", "detail", "error_description"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for nested in _iter_mapping_values(value):
            message = extract_error_message(nested)
            if message:
                return message
        return ""
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for item in value:
            message = extract_error_message(item)
            if message:
                return message
    return ""
