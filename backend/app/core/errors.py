from __future__ import annotations


class ModelNotFoundError(ValueError):
    code = "model_not_found"

    def __init__(self, model: str, message: str | None = None) -> None:
        self.model = model
        self.message = message or f"model '{model}' not found"
        super().__init__(self.message)

    def to_detail(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "model": self.model,
        }
