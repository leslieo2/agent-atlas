from __future__ import annotations

import json
import os
from pathlib import Path

from app.infrastructure.adapters.model_runtime import ModelRuntimeService
from app.modules.shared.domain.enums import AdapterKind


def build_runtime_service() -> ModelRuntimeService:
    return ModelRuntimeService()


def main() -> None:
    request_path = _required_env_path("AFLIGHT_RUN_REQUEST_PATH")
    result_path = _required_env_path("AFLIGHT_RUN_RESULT_PATH")
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    runtime_service = build_runtime_service()

    result = runtime_service.execute(
        AdapterKind(payload["agent_type"]),
        payload["model"],
        payload["prompt"],
    )

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )


def _required_env_path(name: str) -> Path:
    raw = os.getenv(name)
    if not raw:
        raise RuntimeError(f"{name} is required")
    return Path(raw)


if __name__ == "__main__":
    main()
