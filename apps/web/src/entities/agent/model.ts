import type { ProvenanceRecord } from "@/src/shared/api/provenance";

export type AgentPublishState = "draft" | "published";
export type AgentValidationStatus = "valid" | "invalid";

export interface RuntimeArtifactRecord {
  buildStatus?: string | null;
  sourceFingerprint?: string | null;
  framework?: string | null;
  entrypoint?: string | null;
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
  runtimeArtifact?: RuntimeArtifactRecord | null;
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
  runtimeArtifact?: RuntimeArtifactRecord | null;
  provenance?: ProvenanceRecord | null;
}
