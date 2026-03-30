from __future__ import annotations


def build_framework_plugin():
    from app.infrastructure.adapters.openai_agents import build_framework_plugin as builder

    return builder()


__all__ = ["build_framework_plugin"]
