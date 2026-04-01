"use client";

import { ArrowUpRight } from "lucide-react";
import { useMemo } from "react";
import {
  useDiscoveredAgentsQuery,
  usePublishAgentMutation,
  useUnpublishAgentMutation
} from "@/src/entities/agent/query";
import type {
  AgentValidationEvidenceSummaryRecord,
  AgentValidationOutcomeSummaryRecord,
  AgentValidationRunReferenceRecord,
  DiscoveredAgentRecord,
  ExecutionReferenceRecord
} from "@/src/entities/agent/model";
import { executionProfileSummary } from "@/src/shared/runtime/identity";
import { Button } from "@/src/shared/ui/Button";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import { StatusPill } from "@/src/shared/ui/StatusPill";
import styles from "./AgentsWorkspace.module.css";

type AgentGroup = {
  title: string;
  description: string;
  items: DiscoveredAgentRecord[];
};

type AgentReadiness = "ready" | "published_with_drift" | "draft" | "invalid";

function getAgentReadiness(agent: DiscoveredAgentRecord): AgentReadiness {
  if (agent.validationStatus === "invalid") {
    return "invalid";
  }
  if (agent.publishState === "published" && agent.hasUnpublishedChanges) {
    return "published_with_drift";
  }
  if (agent.publishState === "published") {
    return "ready";
  }
  return "draft";
}

function readinessLabel(state: AgentReadiness) {
  if (state === "published_with_drift") {
    return "Draft changes";
  }
  if (state === "ready") {
    return "Ready";
  }
  if (state === "draft") {
    return "Draft";
  }
  return "Invalid";
}

function validationTone(agent: DiscoveredAgentRecord) {
  return agent.validationStatus === "valid" ? "success" : "error";
}

function publishTone(agent: DiscoveredAgentRecord) {
  const readiness = getAgentReadiness(agent);
  return readiness === "ready" ? "success" : "warn";
}

function validationRunTone(status?: string | null) {
  const normalized = status?.trim().toLowerCase() ?? "";
  if (normalized === "succeeded" || normalized === "passed" || normalized === "valid") {
    return "success";
  }
  if (normalized === "failed" || normalized === "runtime_error" || normalized === "invalid") {
    return "error";
  }
  return "warn";
}

function executionReferenceSummary(executionReference?: ExecutionReferenceRecord | null) {
  if (!executionReference) {
    return "-";
  }
  if (executionReference.imageRef) {
    return executionReference.imageRef;
  }
  if (executionReference.artifactRef) {
    return executionReference.artifactRef;
  }
  return "-";
}

function shortSourceFingerprint(sourceFingerprint?: string) {
  const fingerprint = sourceFingerprint?.trim() ?? "";
  if (!fingerprint) {
    return "-";
  }
  return fingerprint.slice(0, 12);
}

function defaultRuntimeSummary(agent: DiscoveredAgentRecord) {
  return executionProfileSummary(agent.defaultRuntimeProfile);
}

function validationIssuesLabel() {
  return "Readiness issues";
}

function formatValidationTimestamp(validationRun?: AgentValidationRunReferenceRecord | null) {
  const value = validationRun?.completedAt ?? validationRun?.startedAt ?? validationRun?.createdAt ?? null;
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString("en");
}

function validationSummaryStatus(
  validationRun?: AgentValidationRunReferenceRecord | null,
  validationOutcome?: AgentValidationOutcomeSummaryRecord | null
) {
  return validationOutcome?.status ?? validationRun?.status ?? "unknown";
}

function validationEvidenceLabel(validationEvidence?: AgentValidationEvidenceSummaryRecord | null) {
  if (!validationEvidence) {
    return "-";
  }
  if (validationEvidence.artifactRef) {
    return validationEvidence.artifactRef;
  }
  if (validationEvidence.imageRef) {
    return validationEvidence.imageRef;
  }
  return "-";
}

function AgentCard({
  agent,
  onPublish,
  onUnpublish,
  isPublishing,
  isUnpublishing
}: {
  agent: DiscoveredAgentRecord;
  onPublish: (agentId: string) => void;
  onUnpublish: (agentId: string) => void;
  isPublishing: boolean;
  isUnpublishing: boolean;
}) {
  const isValid = agent.validationStatus === "valid";
  const isPublished = agent.publishState === "published";
  const readiness = getAgentReadiness(agent);
  const isRunnableSnapshot = readiness === "ready";
  const hasDraftChanges = readiness === "published_with_drift";

  return (
    <article className={styles.card}>
      <div className={styles.cardHeader}>
        <div className={styles.cardTitle}>
          <div>
            <p className="page-eyebrow">Agent</p>
            <h3 className="panel-title">{agent.name}</h3>
          </div>
          <p className="muted-note">{agent.description}</p>
        </div>
        <div className="toolbar">
          <StatusPill tone={publishTone(agent)}>{readinessLabel(readiness)}</StatusPill>
          <StatusPill tone={validationTone(agent)}>{agent.validationStatus}</StatusPill>
        </div>
      </div>

      {hasDraftChanges ? (
        <p className={styles.driftNotice}>
          Re-publish this agent before creating new experiments so Atlas orchestration points at the latest sealed snapshot.
        </p>
      ) : null}

      <div className={styles.meta}>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Agent ID</span>
          <span className={`${styles.metaValue} mono`}>{agent.agentId}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Default model</span>
          <span className={styles.metaValue}>{agent.defaultModel || "-"}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Entrypoint</span>
          <span className={`${styles.metaValue} mono`}>{agent.entrypoint}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Tags</span>
          <span className={styles.metaValue}>{agent.tags.length ? agent.tags.join(", ") : "none"}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Published at</span>
          <span className={styles.metaValue}>{agent.publishedAt ? new Date(agent.publishedAt).toLocaleString("en") : "-"}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Execution ref</span>
          <span className={`${styles.metaValue} mono`}>{executionReferenceSummary(agent.executionReference)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Source fingerprint</span>
          <span className={`${styles.metaValue} mono`}>{shortSourceFingerprint(agent.sourceFingerprint)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Execution profile</span>
          <span className={`${styles.metaValue} mono`}>{defaultRuntimeSummary(agent)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Last validated</span>
          <span className={styles.metaValue}>{new Date(agent.lastValidatedAt).toLocaleString("en")}</span>
        </div>
      </div>

      {agent.latestValidation || agent.validationOutcome || agent.validationEvidence ? (
        <div>
          <div className="toolbar">
            <p className="page-eyebrow">Latest validation</p>
            <StatusPill tone={validationRunTone(validationSummaryStatus(agent.latestValidation, agent.validationOutcome))}>
              {validationSummaryStatus(agent.latestValidation, agent.validationOutcome)}
            </StatusPill>
          </div>
          <div className={styles.meta}>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Validation run</span>
              <span className={`${styles.metaValue} mono`}>{agent.latestValidation?.runId ?? "-"}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Latest evidence</span>
              <span className={`${styles.metaValue} mono`}>{validationEvidenceLabel(agent.validationEvidence)}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Latest outcome</span>
              <span className={styles.metaValue}>{agent.validationOutcome?.reason ?? "Validation summary available"}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Validated at</span>
              <span className={styles.metaValue}>{formatValidationTimestamp(agent.latestValidation)}</span>
            </div>
          </div>
          {agent.validationEvidence?.terminalSummary ? (
            <p className="muted-note">{agent.validationEvidence.terminalSummary}</p>
          ) : null}
          {agent.validationEvidence?.traceUrl ? (
            <Button href={agent.validationEvidence.traceUrl} variant="ghost">
              Open validation trace <ArrowUpRight size={14} />
            </Button>
          ) : null}
        </div>
      ) : null}

      {!isValid ? (
        <div>
          <p className="page-eyebrow">{validationIssuesLabel()}</p>
          <p className="muted-note">Atlas keeps validation on snapshot readiness and provenance, not framework-first routing.</p>
          <ul className={styles.issueList}>
            {agent.validationIssues.map((issue) => (
              <li key={`${agent.agentId}-${issue.code}-${issue.message}`}>{issue.message}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className={styles.actions}>
        {isValid && !isPublished ? (
          <Button onClick={() => onPublish(agent.agentId)} disabled={isPublishing}>
            Publish
          </Button>
        ) : null}
        {isValid && hasDraftChanges ? (
          <Button onClick={() => onPublish(agent.agentId)} disabled={isPublishing}>
            Publish update
          </Button>
        ) : null}
        {isPublished ? (
          <Button variant="secondary" onClick={() => onUnpublish(agent.agentId)} disabled={isUnpublishing}>
            Unpublish
          </Button>
        ) : null}
        {isRunnableSnapshot ? (
          <Button href={`/experiments?agent=${encodeURIComponent(agent.agentId)}`} variant="secondary">
            Create experiment <ArrowUpRight size={14} />
          </Button>
        ) : null}
      </div>
    </article>
  );
}

export default function AgentsWorkspace() {
  const discoveredAgentsQuery = useDiscoveredAgentsQuery();
  const publishMutation = usePublishAgentMutation();
  const unpublishMutation = useUnpublishAgentMutation();
  const agents = useMemo<DiscoveredAgentRecord[]>(() => discoveredAgentsQuery.data ?? [], [discoveredAgentsQuery.data]);

  const groups = useMemo<AgentGroup[]>(
    () => [
      {
        title: "Ready",
        description: "Valid published agents ready to generate RL evaluation data.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "ready")
      },
      {
        title: "Published with draft changes",
        description: "Current repository code differs from the published snapshot.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "published_with_drift")
      },
      {
        title: "Draft",
        description: "Valid agent definitions that are not yet sealed as Atlas snapshots.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "draft")
      },
      {
        title: "Invalid",
        description: "Agent definitions that currently fail readiness or snapshot checks.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "invalid")
      }
    ],
    [agents]
  );

  const errorMessage =
    (publishMutation.error instanceof Error && publishMutation.error.message) ||
    (unpublishMutation.error instanceof Error && unpublishMutation.error.message) ||
    (discoveredAgentsQuery.error instanceof Error && discoveredAgentsQuery.error.message) ||
    "";

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Agent control plane</p>
          <h2 className="section-title">Agents</h2>
          <p className="kicker">
            Govern Atlas agent snapshots, provenance, and execution references before they enter experiment orchestration.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Visible <strong>{agents.length}</strong>
            </span>
            <span className="page-tag">
              Ready to run <strong>{groups[0].items.length}</strong>
            </span>
            <span className="page-tag">
              Needs review <strong>{groups[1].items.length + groups[3].items.length}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Publishing status</span>
            <span className="page-info-value">
              {groups[0].items.length} ready / {groups[1].items.length} drifted / {groups[2].items.length} staged /{" "}
              {groups[3].items.length} invalid
            </span>
            <p className="page-info-detail">
              Only ready snapshots can seed new experiments. Re-publish drifted agents to refresh Atlas-owned provenance.
            </p>
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Ready" value={groups[0].items.length} />
        <MetricCard label="Draft changes" value={groups[1].items.length} />
        <MetricCard label="Draft" value={groups[2].items.length} />
        <MetricCard label="Invalid" value={groups[3].items.length} />
      </div>

      {errorMessage ? <Notice>{errorMessage}</Notice> : null}
      {discoveredAgentsQuery.isLoading ? <Notice>Loading agents...</Notice> : null}

      {groups.map((group) => (
        <Panel key={group.title} tone="plain" className={styles.group}>
          <div className="surface-header">
            <div>
              <p className="surface-kicker">{group.title}</p>
              <h3 className="panel-title">{group.description}</h3>
              <p className="muted-note">{group.items.length} agents in this section.</p>
            </div>
          </div>

          {group.items.length ? (
            <div className={styles.cards}>
              {group.items.map((agent) => (
                <AgentCard
                  key={`${group.title}-${agent.agentId}`}
                  agent={agent}
                  onPublish={(agentId) => publishMutation.mutate(agentId)}
                  onUnpublish={(agentId) => unpublishMutation.mutate(agentId)}
                  isPublishing={publishMutation.isPending}
                  isUnpublishing={unpublishMutation.isPending}
                />
              ))}
            </div>
          ) : (
            <Notice>No agents in this section.</Notice>
          )}
        </Panel>
      ))}
    </section>
  );
}
