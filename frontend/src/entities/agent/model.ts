import type { ProvenanceRecord } from "@/src/shared/api/provenance";

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
  provenance?: ProvenanceRecord | null;
}

export interface AgentValidationIssueRecord {
  code: string;
  message: string;
}

export interface DiscoveredAgentRecord extends AgentRecord {
  publishState: AgentPublishState;
  validationStatus: AgentValidationStatus;
  validationIssues: AgentValidationIssueRecord[];
  publishedAt?: string;
  lastValidatedAt: string;
  hasUnpublishedChanges: boolean;
  provenance?: ProvenanceRecord | null;
}
