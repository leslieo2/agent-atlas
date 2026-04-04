import type { ExecutionProfile, ExecutionProfileRequest } from "@/src/shared/api/contract";

export interface ExecutionReferenceRecord {
  artifactRef?: string | null;
  imageRef?: string | null;
}

export interface AgentValidationRunReferenceRecord {
  runId: string;
  status: string;
  createdAt: string;
  startedAt?: string | null;
  completedAt?: string | null;
}

export interface AgentValidationEvidenceSummaryRecord {
  artifactRef?: string | null;
  imageRef?: string | null;
  traceUrl?: string | null;
  terminalSummary?: string | null;
}

export interface AgentValidationOutcomeSummaryRecord {
  status: string;
  reason?: string | null;
}

export type ExecutionProfileRecord = ExecutionProfileRequest & {
  metadata?: Record<string, unknown>;
  runner_image?: string;
  artifact_path?: string;
  binding?: Record<string, unknown>;
  execution_binding?: Record<string, unknown>;
  timeout_seconds?: number;
  max_steps?: number;
  concurrency?: number;
  resources?: Record<string, unknown>;
};

export interface AgentRecord {
  agentId: string;
  name: string;
  description: string;
  agentFamily?: string;
  framework: string;
  frameworkVersion: string;
  entrypoint: string;
  defaultModel: string;
  tags: string[];
  capabilities: string[];
  publishedAt?: string;
  sourceFingerprint?: string;
  executionReference?: ExecutionReferenceRecord | null;
  executionProfile: ExecutionProfileRecord;
  latestValidation?: AgentValidationRunReferenceRecord | null;
  validationEvidence?: AgentValidationEvidenceSummaryRecord | null;
  validationOutcome?: AgentValidationOutcomeSummaryRecord | null;
}

export interface AgentValidationIssueRecord {
  code: string;
  message: string;
}
