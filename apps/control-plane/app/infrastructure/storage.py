from __future__ import annotations

from typing import Protocol

from app.db.persistence import PlaneStoreSet
from app.modules.agents.adapters.outbound.persistence import StatePublishedAgentRepository
from app.modules.datasets.adapters.outbound.persistence import StateDatasetRepository
from app.modules.experiments.adapters.outbound.persistence import (
    StateExperimentRepository,
    StateRunEvaluationRepository,
)
from app.modules.exports.adapters.outbound.persistence import StateExportRepository
from app.modules.policies.adapters.outbound.persistence import StateApprovalPolicyRepository
from app.modules.runs.adapters.outbound.persistence import (
    StateRunRepository,
    StateTraceRepository,
    StateTrajectoryRepository,
)


class StateStorageContributor(Protocol):
    def init_schema(self) -> None: ...

    def reset_state(self) -> None: ...


def build_storage_contributors(stores: PlaneStoreSet) -> list[StateStorageContributor]:
    return [
        StateRunRepository(stores),
        StateTrajectoryRepository(stores),
        StateTraceRepository(stores),
        StateDatasetRepository(stores),
        StateExperimentRepository(stores),
        StateRunEvaluationRepository(stores),
        StateExportRepository(stores),
        StateApprovalPolicyRepository(stores),
        StatePublishedAgentRepository(stores),
    ]


__all__ = ["StateStorageContributor", "build_storage_contributors"]
