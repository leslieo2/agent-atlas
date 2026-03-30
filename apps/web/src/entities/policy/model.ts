export interface ToolPolicyRuleRecord {
  toolName: string;
  effect: "allow" | "deny";
  description?: string | null;
}

export interface ApprovalPolicyRecord {
  approvalPolicyId: string;
  name: string;
  description?: string | null;
  toolPolicies: ToolPolicyRuleRecord[];
  createdAt: string;
}
