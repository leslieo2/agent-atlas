from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.bootstrap.container import get_adapter_queries
from app.modules.adapters.api.schemas import AdapterDescriptorResponse
from app.modules.adapters.application.use_cases import AdapterQueries

router = APIRouter(prefix="/adapters", tags=["adapters"])


@router.get("", response_model=list[AdapterDescriptorResponse])
def list_adapters(
    queries: Annotated[AdapterQueries, Depends(get_adapter_queries)],
):
    return [AdapterDescriptorResponse.from_domain(adapter) for adapter in queries.list_adapters()]
