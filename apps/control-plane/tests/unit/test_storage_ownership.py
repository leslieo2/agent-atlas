from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from app.db.persistence import PlaneStoreSet
from app.modules.exports.adapters.outbound import StateExportRepository
from app.modules.exports.domain.models import ArtifactMetadata
from app.modules.runs.adapters.outbound import (
    StateRunRepository,
    StateTraceRepository,
    StateTrajectoryRepository,
)
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.enums import AdapterKind, ArtifactFormat, RunStatus, StepType
from app.modules.shared.domain.models import TrajectoryStepRecord
from app.modules.shared.domain.traces import TraceSpan


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def _run_record() -> RunRecord:
    return RunRecord(
        run_id=uuid4(),
        input_summary="storage split",
        project="control-plane",
        dataset="crm-v2",
        model="gpt-5.4-mini",
        agent_type=AdapterKind.OPENAI_AGENTS,
        status=RunStatus.RUNNING,
    )


def test_storage_ownership_uses_plane_prefixed_tables_in_shared_sqlite_db(tmp_path: Path) -> None:
    db_path = tmp_path / "atlas-shared.db"
    stores = PlaneStoreSet(
        control_database_url=_sqlite_url(db_path),
        data_database_url=_sqlite_url(db_path),
    )
    try:
        run_repository = StateRunRepository(stores)
        trajectory_repository = StateTrajectoryRepository(stores)
        export_repository = StateExportRepository(stores)
        run = _run_record()

        run_repository.save(run)
        trajectory_repository.append(
            TrajectoryStepRecord(
                id="step-1",
                run_id=run.run_id,
                step_type=StepType.LLM,
                prompt="Explain the plan.",
                output="Plan explained.",
            )
        )
        export_repository.save(
            ArtifactMetadata(
                format=ArtifactFormat.JSONL,
                path="s3://exports/atlas-run-1.jsonl",
                size_bytes=128,
                row_count=1,
            )
        )

        conn = sqlite3.connect(db_path)
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }

            assert {"control_runs", "data_trajectory", "data_artifacts"} <= tables
            assert "runs" not in tables
            assert "trajectory" not in tables
            assert conn.execute("SELECT COUNT(*) FROM control_runs").fetchone()[0] == 1
            assert conn.execute("SELECT COUNT(*) FROM data_trajectory").fetchone()[0] == 1
            assert conn.execute("SELECT COUNT(*) FROM data_artifacts").fetchone()[0] == 1
        finally:
            conn.close()
    finally:
        stores.close()


def test_storage_ownership_can_split_planes_across_distinct_sqlite_files(tmp_path: Path) -> None:
    control_db = tmp_path / "control.db"
    data_db = tmp_path / "data.db"
    stores = PlaneStoreSet(
        control_database_url=_sqlite_url(control_db),
        data_database_url=_sqlite_url(data_db),
    )
    try:
        run_repository = StateRunRepository(stores)
        trace_repository = StateTraceRepository(stores)
        run = _run_record()

        run_repository.save(run)
        trace_repository.append(
            TraceSpan(
                run_id=run.run_id,
                span_id="span-1",
                parent_span_id=None,
                step_type=StepType.LLM,
                input={"prompt": "Check ownership split"},
                output={"output": "split confirmed"},
                latency_ms=5,
                token_usage=11,
            )
        )

        control_conn = sqlite3.connect(control_db)
        data_conn = sqlite3.connect(data_db)
        try:
            control_tables = {
                row[0]
                for row in control_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            data_tables = {
                row[0]
                for row in data_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }

            assert "control_runs" in control_tables
            assert "data_trace_spans" not in control_tables
            assert "data_trace_spans" in data_tables
            assert "control_runs" not in data_tables
            assert control_conn.execute("SELECT COUNT(*) FROM control_runs").fetchone()[0] == 1
            assert data_conn.execute("SELECT COUNT(*) FROM data_trace_spans").fetchone()[0] == 1
        finally:
            control_conn.close()
            data_conn.close()
    finally:
        stores.close()
