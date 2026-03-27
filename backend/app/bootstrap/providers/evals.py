from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.evals.application.use_cases import EvalJobCommands, EvalJobQueries


def get_eval_queries() -> EvalJobQueries:
    return get_container().evals.eval_queries


def get_eval_commands() -> EvalJobCommands:
    return get_container().evals.eval_commands
