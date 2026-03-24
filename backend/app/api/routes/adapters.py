from __future__ import annotations

from fastapi import APIRouter

from app.services.adapter import adapter_manager

router = APIRouter(prefix="/adapters", tags=["adapters"])


@router.get("")
def list_adapters():
    return adapter_manager.list_adapters()
