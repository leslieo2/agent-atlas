from __future__ import annotations


def build_framework_plugin():
    from app.infrastructure.adapters.langchain import build_framework_plugin as builder

    return builder()


__all__ = ["build_framework_plugin"]
