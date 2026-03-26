from __future__ import annotations

from importlib import import_module
from typing import Any
from uuid import UUID

from app.agent_registry import get_registered_agent, list_registered_agents
from app.core.errors import AgentLoadFailedError
from app.modules.agents.domain.models import AgentDescriptor
from app.registered_agents.context import RegisteredAgentBuildContext


def _validation_context() -> RegisteredAgentBuildContext:
    return RegisteredAgentBuildContext(
        run_id=UUID("00000000-0000-0000-0000-000000000000"),
        project="validation",
        dataset=None,
        prompt="validation",
        tags=[],
        project_metadata={},
    )


class StateAgentCatalog:
    def list_agents(self) -> list[AgentDescriptor]:
        return [self._validate_descriptor(entry.agent_id) for entry in list_registered_agents()]

    def get_agent(self, agent_id: str) -> AgentDescriptor | None:
        registered = get_registered_agent(agent_id)
        if registered is None:
            return None
        return self._validate_descriptor(agent_id)

    def _validate_descriptor(self, agent_id: str) -> AgentDescriptor:
        registered = get_registered_agent(agent_id)
        if registered is None:
            raise AgentLoadFailedError(
                f"registered agent '{agent_id}' not found during validation",
                agent_id=agent_id,
            )

        agent = self.build_agent(agent_id, context=_validation_context())
        try:
            from agents import Agent
        except ImportError as exc:
            raise AgentLoadFailedError(
                "OpenAI Agents SDK package 'agents' is not installed",
                agent_id=agent_id,
            ) from exc

        if not isinstance(agent, Agent):
            raise AgentLoadFailedError(
                f"entrypoint '{registered.entrypoint}' did not return an OpenAI Agents SDK Agent",
                agent_id=agent_id,
            )

        return AgentDescriptor(
            agent_id=registered.agent_id,
            name=registered.name,
            description=registered.description,
            framework=registered.framework,
            entrypoint=registered.entrypoint,
            default_model=registered.default_model,
            tags=registered.tags,
        )

    def build_agent(self, agent_id: str, context: RegisteredAgentBuildContext) -> Any:
        registered = get_registered_agent(agent_id)
        if registered is None:
            raise AgentLoadFailedError(
                f"registered agent '{agent_id}' not found during build",
                agent_id=agent_id,
            )

        module_name, _, symbol_name = registered.entrypoint.partition(":")
        if not module_name or not symbol_name:
            raise AgentLoadFailedError(
                f"invalid entrypoint '{registered.entrypoint}'",
                agent_id=agent_id,
            )

        try:
            module = import_module(module_name)
        except Exception as exc:
            raise AgentLoadFailedError(
                f"failed to import module '{module_name}'",
                agent_id=agent_id,
                entrypoint=registered.entrypoint,
            ) from exc

        symbol = getattr(module, symbol_name, None)
        if symbol is None:
            raise AgentLoadFailedError(
                f"symbol '{symbol_name}' not found in module '{module_name}'",
                agent_id=agent_id,
                entrypoint=registered.entrypoint,
            )
        if not callable(symbol):
            raise AgentLoadFailedError(
                f"symbol '{symbol_name}' is not callable",
                agent_id=agent_id,
                entrypoint=registered.entrypoint,
            )

        try:
            return symbol(context)
        except Exception as exc:
            raise AgentLoadFailedError(
                f"failed to build registered agent '{agent_id}'",
                agent_id=agent_id,
                entrypoint=registered.entrypoint,
            ) from exc
