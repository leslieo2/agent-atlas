export type AgentPublishState = "draft" | "published";
export type AgentValidationStatus = "valid" | "invalid";

export interface AgentRecord {
  agentId: string;
  name: string;
  description: string;
  framework: string;
  entrypoint: string;
  defaultModel: string;
  tags: string[];
  publishedAt?: string;
}

export interface AgentValidationIssueRecord {
  code: string;
  message: string;
}

export interface DiscoveredAgentRecord extends AgentRecord {
  publishState: AgentPublishState;
  validationStatus: AgentValidationStatus;
  validationIssues: AgentValidationIssueRecord[];
}
