from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    agent_router,
    dataset_router,
    experiment_router,
    export_router,
    policy_router,
    run_router,
)
from app.bootstrap.providers.health import get_health_queries
from app.bootstrap.seed import seed_demo_state
from app.core.config import settings
from app.modules.health.application.use_cases import HealthQueries


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.should_seed_demo():
        seed_demo_state()
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
def health(queries: Annotated[HealthQueries, Depends(get_health_queries)]):
    return queries.get_health()


app.include_router(agent_router, prefix=settings.api_prefix)
app.include_router(dataset_router, prefix=settings.api_prefix)
app.include_router(experiment_router, prefix=settings.api_prefix)
app.include_router(export_router, prefix=settings.api_prefix)
app.include_router(policy_router, prefix=settings.api_prefix)
app.include_router(run_router, prefix=settings.api_prefix)
