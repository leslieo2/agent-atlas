import { request } from "@/src/shared/api/http";
import type { ApprovalPolicyResponse } from "@/src/shared/api/contract";
import type { ApprovalPolicyRecord } from "./model";

function mapPolicy(policy: ApprovalPolicyResponse): ApprovalPolicyRecord {
  return {
    approvalPolicyId: policy.approval_policy_id,
    name: policy.name,
    description: policy.description ?? null,
    toolPolicies: policy.tool_policies.map((rule) => ({
      toolName: rule.tool_name,
      effect: rule.effect,
      description: rule.description ?? null
    })),
    createdAt: policy.created_at
  };
}

export async function listPolicies() {
  return (await request<ApprovalPolicyResponse[]>("/api/v1/policies")).map(mapPolicy);
}
