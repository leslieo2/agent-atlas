import type { ExecutorConfig } from "@/src/shared/api/contract";

export type AgentPublishState = "draft" | "published";
export type AgentValidationStatus = "valid" | "invalid";

export interface ExecutionReferenceRecord {
  artifactRef?: string | null;
  imageRef?: string | null;
}

export interface AgentRecord {
  agentId: string;
  name: string;
  description: string;
  framework: string;
  frameworkVersion: string;
  entrypoint: string;
  defaultModel: string;
  tags: string[];
  capabilities: string[];
  publishedAt?: string;
  sourceFingerprint?: string;
  executionReference?: ExecutionReferenceRecord | null;
  defaultRuntimeProfile: ExecutorConfig;
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
  sourceFingerprint?: string;
  executionReference?: ExecutionReferenceRecord | null;
  defaultRuntimeProfile: ExecutorConfig;
}
