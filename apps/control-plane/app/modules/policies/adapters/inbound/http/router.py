from __future__ import annotations

from typing import Annotated

from app.bootstrap.providers.policies import get_policy_commands, get_policy_queries
from app.modules.policies.adapters.inbound.http.schemas import (
    ApprovalPolicyCreateRequest,
    ApprovalPolicyResponse,
)
from app.modules.policies.application.use_cases import PolicyCommands, PolicyQueries
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[ApprovalPolicyResponse])
def list_policies(
    queries: Annotated[PolicyQueries, Depends(get_policy_queries)],
) -> list[ApprovalPolicyResponse]:
    return [ApprovalPolicyResponse.from_domain(item) for item in queries.list()]


@router.get("/{approval_policy_id}", response_model=ApprovalPolicyResponse)
def get_policy(
    approval_policy_id: str,
    queries: Annotated[PolicyQueries, Depends(get_policy_queries)],
) -> ApprovalPolicyResponse:
    policy = queries.get(approval_policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="approval policy not found")
    return ApprovalPolicyResponse.from_domain(policy)


@router.post("", response_model=ApprovalPolicyResponse)
def create_policy(
    payload: ApprovalPolicyCreateRequest,
    commands: Annotated[PolicyCommands, Depends(get_policy_commands)],
) -> ApprovalPolicyResponse:
    return ApprovalPolicyResponse.from_domain(commands.create(payload.to_domain()))
