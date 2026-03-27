from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.bootstrap.wiring.agents import AgentModuleBundle, build_agent_module
from app.bootstrap.wiring.artifacts import ArtifactModuleBundle, build_artifact_module
from app.bootstrap.wiring.datasets import DatasetModuleBundle, build_dataset_module
from app.bootstrap.wiring.evals import EvalModuleBundle, build_eval_module
from app.bootstrap.wiring.health import HealthModuleBundle, build_health_module
from app.bootstrap.wiring.infrastructure import InfrastructureBundle, build_infrastructure
from app.bootstrap.wiring.runs import RunModuleBundle, build_run_module
from app.bootstrap.wiring.traces import TraceModuleBundle, build_trace_module
from app.bootstrap.wiring.worker import WorkerBundle, build_worker_bundle


@dataclass(frozen=True)
class AppContainer:
    infrastructure: InfrastructureBundle
    agents: AgentModuleBundle
    traces: TraceModuleBundle
    datasets: DatasetModuleBundle
    runs: RunModuleBundle
    evals: EvalModuleBundle
    artifacts: ArtifactModuleBundle
    health: HealthModuleBundle
    worker: WorkerBundle


@lru_cache
def get_container() -> AppContainer:
    infrastructure = build_infrastructure()
    agents = build_agent_module(infrastructure)
    traces = build_trace_module(infrastructure)
    datasets = build_dataset_module(infrastructure)
    runs = build_run_module(infrastructure, traces)
    evals = build_eval_module(infrastructure, agents, runs)
    artifacts = build_artifact_module(infrastructure)
    health = build_health_module(infrastructure)
    worker = build_worker_bundle(infrastructure, runs, evals)

    return AppContainer(
        infrastructure=infrastructure,
        agents=agents,
        traces=traces,
        datasets=datasets,
        runs=runs,
        evals=evals,
        artifacts=artifacts,
        health=health,
        worker=worker,
    )
