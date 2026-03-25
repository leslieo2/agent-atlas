from __future__ import annotations

from app.db.persistence import build_state_persistence, to_uuid
from app.modules.adapters.domain.models import AdapterDescriptor
from app.modules.shared.domain.enums import AdapterKind

persistence = build_state_persistence()

ADAPTER_CATALOG = [
    AdapterDescriptor(
        kind=AdapterKind.OPENAI_AGENTS,
        name="OpenAI Agents SDK",
        runtime_version="stable",
        notes="SQLite-backed workbench runtime adapter with OpenAI-compatible traces",
        supports_replay=True,
        supports_eval=True,
    ),
    AdapterDescriptor(
        kind=AdapterKind.LANGCHAIN,
        name="LangChain",
        runtime_version="stable",
        notes="LangChain ChatOpenAI runtime bridge",
        supports_replay=True,
        supports_eval=True,
    ),
    AdapterDescriptor(
        kind=AdapterKind.MCP,
        name="MCP Tool Shim",
        runtime_version="v1",
        notes="Tool integration facade for external MCP servers",
        supports_replay=False,
        supports_eval=False,
    ),
]

__all__ = ["ADAPTER_CATALOG", "persistence", "to_uuid"]
