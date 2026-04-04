from __future__ import annotations


class RunnableGraph:
    def invoke(self, payload: object) -> dict[str, str]:
        del payload
        return {"output": "graph response"}


def build_agent(_context: object) -> RunnableGraph:
    return RunnableGraph()
