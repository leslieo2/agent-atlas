from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    adapter_router,
    artifact_router,
    dataset_router,
    eval_router,
    replay_router,
    run_router,
    trace_router,
)
from app.core.config import settings
from app.db.state import state
from app.services.seed import bootstrap


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "components": {
            "state_initialized": bool(state.runs is not None),
            "state_persistence_enabled": bool(state.persist.enabled),
        },
    }


app.include_router(run_router, prefix=settings.api_prefix)
app.include_router(replay_router, prefix=settings.api_prefix)
app.include_router(eval_router, prefix=settings.api_prefix)
app.include_router(dataset_router, prefix=settings.api_prefix)
app.include_router(artifact_router, prefix=settings.api_prefix)
app.include_router(trace_router, prefix=settings.api_prefix)
app.include_router(adapter_router, prefix=settings.api_prefix)
