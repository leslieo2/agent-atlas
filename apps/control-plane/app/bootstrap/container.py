from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.bootstrap.wiring.agents import AgentModuleBundle, build_agent_module
from app.bootstrap.wiring.datasets import DatasetModuleBundle, build_dataset_module
from app.bootstrap.wiring.experiments import ExperimentModuleBundle, build_experiment_module
from app.bootstrap.wiring.exports import ExportModuleBundle, build_export_module
from app.bootstrap.wiring.health import HealthModuleBundle, build_health_module
from app.bootstrap.wiring.infrastructure import InfrastructureBundle, build_infrastructure
from app.bootstrap.wiring.jobs import JobBundle, build_job_bundle
from app.bootstrap.wiring.policies import PolicyModuleBundle, build_policy_module
from app.bootstrap.wiring.runs import RunModuleBundle, build_run_module


@dataclass(frozen=True)
class AppContainer:
    infrastructure: InfrastructureBundle
    agents: AgentModuleBundle
    datasets: DatasetModuleBundle
    runs: RunModuleBundle
    experiments: ExperimentModuleBundle
    exports: ExportModuleBundle
    policies: PolicyModuleBundle
    health: HealthModuleBundle
    jobs: JobBundle


@lru_cache
def get_container() -> AppContainer:
    infrastructure = build_infrastructure()
    agents = build_agent_module(infrastructure)
    datasets = build_dataset_module(infrastructure)
    runs = build_run_module(infrastructure)
    experiments = build_experiment_module(infrastructure, agents, runs)
    exports = build_export_module(infrastructure)
    policies = build_policy_module(infrastructure)
    health = build_health_module(infrastructure)
    jobs = build_job_bundle(runs, experiments)

    return AppContainer(
        infrastructure=infrastructure,
        agents=agents,
        datasets=datasets,
        runs=runs,
        experiments=experiments,
        exports=exports,
        policies=policies,
        health=health,
        jobs=jobs,
    )
