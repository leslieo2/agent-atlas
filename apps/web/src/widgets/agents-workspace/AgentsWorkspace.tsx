"use client";

import { ArrowUpRight } from "lucide-react";
import { useMemo, useState } from "react";
import {
  useBootstrapClaudeCodeAgentMutation,
  useDiscoveredAgentsQuery,
  usePublishedAgentsQuery,
  usePublishAgentMutation,
  useStartValidationRunMutation,
  useUnpublishAgentMutation
} from "@/src/entities/agent/query";
import { getAgentValidationLifecycle } from "@/src/entities/agent/lifecycle";
import type {
  AgentRecord,
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
  items: AgentWorkspaceRecord[];
};

type AgentReadiness = "ready" | "validating" | "needs_review" | "published_with_drift" | "draft" | "invalid";

type AgentWorkspaceRecord = DiscoveredAgentRecord & {
  dataSource: "discovered" | "published";
};

function fallbackValidationTimestamp(agent: AgentRecord) {
  return (
    agent.latestValidation?.completedAt ??
    agent.latestValidation?.startedAt ??
    agent.latestValidation?.createdAt ??
    agent.publishedAt ??
    new Date(0).toISOString()
  );
}

function inferValidationStatus(agent: AgentRecord) {
  const validationLifecycle = getAgentValidationLifecycle(agent);
  if (validationLifecycle.status === "failed" || validationLifecycle.status === "cancelled" || validationLifecycle.status === "lost") {
    return "invalid" as const;
  }
  return "valid" as const;
}

function mapPublishedAgent(agent: AgentRecord): AgentWorkspaceRecord {
  return {
    ...agent,
    publishState: "published",
    validationStatus: inferValidationStatus(agent),
    validationIssues: [],
    lastValidatedAt: fallbackValidationTimestamp(agent),
    hasUnpublishedChanges: false,
    dataSource: "published"
  };
}

function getAgentReadiness(agent: DiscoveredAgentRecord): AgentReadiness {
  const validationLifecycle = getAgentValidationLifecycle(agent);
  if (agent.validationStatus === "invalid") {
    return "invalid";
  }
  if (validationLifecycle.isActive) {
    return "validating";
  }
  if (validationLifecycle.isBlocking) {
    return "needs_review";
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
  if (state === "validating") {
    return "Validating";
  }
  if (state === "needs_review") {
    return "Needs review";
  }
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
  return getAgentValidationLifecycle(agent).tone;
}

function publishTone(agent: DiscoveredAgentRecord) {
  const readiness = getAgentReadiness(agent);
  return readiness === "ready" ? "success" : "warn";
}

function validationRunTone(status?: string | null) {
  return getAgentValidationLifecycle({
    latestValidation: status ? ({ status } as AgentValidationRunReferenceRecord) : null,
    validationOutcome: null
  }).tone;
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
  return validationRun?.status ?? validationOutcome?.status ?? "unknown";
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

function hasBlockingValidationOutcome(agent: DiscoveredAgentRecord) {
  return getAgentValidationLifecycle(agent).isBlocking;
}

function nextStepLabel(agent: DiscoveredAgentRecord) {
  const readiness = getAgentReadiness(agent);
  if (readiness === "invalid") {
    return "Resolve readiness issues before Atlas can seal, validate, or hand off this asset.";
  }
  if (readiness === "validating") {
    return "Atlas is still running the latest validation. Wait for the active run to finish before handing this snapshot into experiments.";
  }
  if (readiness === "needs_review") {
    return "Review the latest validation run and evidence before handing this snapshot into a new experiment.";
  }
  if (readiness === "published_with_drift") {
    return "Re-publish this asset so new experiments use the latest governed snapshot.";
  }
  if (readiness === "draft") {
    return "Publish this validated draft when you want Atlas to hand it into experiments.";
  }
  if (hasBlockingValidationOutcome(agent)) {
    return "Review the latest validation evidence before handing this snapshot into a new experiment.";
  }
  return "Hand this ready snapshot into the next experiment.";
}

function validationPayload(agent: DiscoveredAgentRecord) {
  return {
    project: "atlas-validation",
    dataset: "controlled-validation",
    input_summary: `Validate ${agent.name} from the Agents surface`,
    prompt: "alpha",
    tags: ["agents-surface"],
    project_metadata: {
      validation_target: agent.agentId,
      validation_surface: "agents"
    },
    executor_config: agent.defaultRuntimeProfile
  };
}

function AgentCard({
  agent,
  onPublish,
  onUnpublish,
  onValidate,
  isPublishing,
  isUnpublishing,
  isValidating
}: {
  agent: DiscoveredAgentRecord;
  onPublish: (agentId: string) => void;
  onUnpublish: (agentId: string) => void;
  onValidate: (agent: DiscoveredAgentRecord) => void;
  isPublishing: boolean;
  isUnpublishing: boolean;
  isValidating: boolean;
}) {
  const validationLifecycle = getAgentValidationLifecycle(agent);
  const isValid = agent.validationStatus === "valid";
  const isPublished = agent.publishState === "published";
  const readiness = getAgentReadiness(agent);
  const isRunnableSnapshot = readiness === "ready" && !validationLifecycle.isBlocking && !validationLifecycle.isActive;
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
          <StatusPill tone={validationTone(agent)}>{validationLifecycle.status}</StatusPill>
        </div>
      </div>

      {hasDraftChanges ? (
        <p className={styles.driftNotice}>
          Re-publish this asset before creating new experiments so Atlas orchestration points at the latest governed snapshot.
        </p>
      ) : null}
      {readiness === "validating" ? (
        <p className={styles.driftNotice}>
          Atlas is projecting this asset from the active validation run. The experiment handoff stays blocked until that run resolves.
        </p>
      ) : null}

      <div>
        <p className="page-eyebrow">Next step</p>
        <p className="muted-note">{nextStepLabel(agent)}</p>
      </div>

      {agent.latestValidation || agent.validationOutcome || agent.validationEvidence ? (
        <div>
          <div className="toolbar">
            <p className="page-eyebrow">Latest validation</p>
            <StatusPill tone={validationRunTone(validationSummaryStatus(agent.latestValidation, agent.validationOutcome))}>
              {validationSummaryStatus(agent.latestValidation, agent.validationOutcome)}
            </StatusPill>
          </div>
          <p className="muted-note">
            {agent.validationOutcome?.reason ?? "Validation evidence is available for the latest run."}
          </p>
          <div className={styles.meta}>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Validation run</span>
              <span className={`${styles.metaValue} mono`}>{agent.latestValidation?.runId ?? "-"}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Validated at</span>
              <span className={styles.metaValue}>{formatValidationTimestamp(agent.latestValidation)}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Evidence ref</span>
              <span className={`${styles.metaValue} mono`}>{validationEvidenceLabel(agent.validationEvidence)}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Outcome</span>
              <span className={styles.metaValue}>{agent.validationOutcome?.reason ?? "Validation summary available"}</span>
            </div>
          </div>
          {agent.validationEvidence?.terminalSummary ? (
            <p className="muted-note">{agent.validationEvidence.terminalSummary}</p>
          ) : null}
          {agent.validationEvidence?.traceUrl ? (
            <Button href={agent.validationEvidence.traceUrl} variant="ghost">
              Open validation evidence <ArrowUpRight size={14} />
            </Button>
          ) : null}
        </div>
      ) : null}

      <div className={styles.meta}>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Execution profile</span>
          <span className={`${styles.metaValue} mono`}>{defaultRuntimeSummary(agent)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Last validated</span>
          <span className={styles.metaValue}>{new Date(agent.lastValidatedAt).toLocaleString("en")}</span>
        </div>
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
      </div>

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
        {isValid ? (
          <Button variant="secondary" onClick={() => onValidate(agent)} disabled={isValidating}>
            Run validation
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
  const publishedAgentsQuery = usePublishedAgentsQuery();
  const bootstrapMutation = useBootstrapClaudeCodeAgentMutation();
  const publishMutation = usePublishAgentMutation();
  const unpublishMutation = useUnpublishAgentMutation();
  const validationMutation = useStartValidationRunMutation();
  const [actionMessage, setActionMessage] = useState("");
  const agents = useMemo<AgentWorkspaceRecord[]>(() => {
    const discovered = (discoveredAgentsQuery.data ?? []).map((agent) => ({ ...agent, dataSource: "discovered" as const }));
    const discoveredIds = new Set(discovered.map((agent) => agent.agentId));
    const publishedOnly = (publishedAgentsQuery.data ?? [])
      .filter((agent) => !discoveredIds.has(agent.agentId))
      .map(mapPublishedAgent);
    return [...discovered, ...publishedOnly];
  }, [discoveredAgentsQuery.data, publishedAgentsQuery.data]);

  const groups = useMemo<AgentGroup[]>(
    () => [
      {
        title: "Ready",
        description: "Governed published assets ready to generate RL evaluation data.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "ready")
      },
      {
        title: "Validating",
        description: "Assets with an active validation run that still owns the current lifecycle state.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "validating")
      },
      {
        title: "Needs review",
        description: "Assets whose latest validation run ended in a blocking state and need evidence review before handoff.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "needs_review")
      },
      {
        title: "Published with draft changes",
        description: "Current repository code differs from the governed published snapshot.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "published_with_drift")
      },
      {
        title: "Draft",
        description: "Valid agent definitions that are not yet sealed as governed Atlas snapshots.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "draft")
      },
      {
        title: "Invalid",
        description: "Agent definitions that currently fail governance, readiness, or snapshot checks.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "invalid")
      }
    ],
    [agents]
  );

  const errorMessage =
    (bootstrapMutation.error instanceof Error && bootstrapMutation.error.message) ||
    (publishMutation.error instanceof Error && publishMutation.error.message) ||
    (unpublishMutation.error instanceof Error && unpublishMutation.error.message) ||
    (validationMutation.error instanceof Error && validationMutation.error.message) ||
    (discoveredAgentsQuery.error instanceof Error && discoveredAgentsQuery.error.message) ||
    (publishedAgentsQuery.error instanceof Error && publishedAgentsQuery.error.message) ||
    "";

  const isLoading = discoveredAgentsQuery.isLoading || publishedAgentsQuery.isLoading;

  async function handleBootstrap() {
    try {
      const agent = await bootstrapMutation.mutateAsync();
      setActionMessage(
        `Created ${agent.name}. Atlas can now validate it, return it to draft, or hand the governed snapshot into experiments from this surface.`
      );
    } catch {
      // Error state is surfaced through the shared notice area.
    }
  }

  async function handleValidation(agent: DiscoveredAgentRecord) {
    try {
      const run = await validationMutation.mutateAsync({
        agentId: agent.agentId,
        payload: validationPayload(agent)
      });
      setActionMessage(
        `Started validation run ${run.run_id} for ${agent.name}. Atlas will attach the latest validation evidence here so the asset handoff stays explicit.`
      );
    } catch {
      // Error state is surfaced through the shared notice area.
    }
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Agent control plane</p>
          <h2 className="section-title">Agents</h2>
          <p className="kicker">
            Govern formal agent assets, review the latest validation evidence, and hand the right snapshot into
            experiment orchestration.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Visible <strong>{agents.length}</strong>
            </span>
            <span className="page-tag">
              Ready to run <strong>{groups[0].items.length}</strong>
            </span>
            <span className="page-tag">
              Needs review <strong>{groups[2].items.length + groups[3].items.length + groups[5].items.length}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Publishing status</span>
            <span className="page-info-value">
              {groups[0].items.length} ready / {groups[1].items.length} validating / {groups[2].items.length} review /{" "}
              {groups[3].items.length} drifted / {groups[4].items.length} staged / {groups[5].items.length} invalid
            </span>
            <p className="page-info-detail">
              Start with governed snapshots, re-publish drifted ones, and use the latest validation summary to decide
              what to hand off next.
            </p>
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Ready" value={groups[0].items.length} />
        <MetricCard label="Validating" value={groups[1].items.length} />
        <MetricCard label="Needs review" value={groups[2].items.length} />
        <MetricCard label="Draft changes" value={groups[3].items.length} />
        <MetricCard label="Draft" value={groups[4].items.length} />
        <MetricCard label="Invalid" value={groups[5].items.length} />
      </div>

      {actionMessage ? <Notice>{actionMessage}</Notice> : null}
      {errorMessage ? <Notice>{errorMessage}</Notice> : null}
      {isLoading ? <Notice>Loading agents...</Notice> : null}
      {!isLoading && !agents.length ? (
        <Panel tone="plain">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">No agents yet</p>
              <h3 className="panel-title">Bootstrap the first governed Claude Code asset</h3>
              <p className="muted-note">
                Governed snapshots appear here once Atlas creates the first Claude Code starter asset from the existing
                bootstrap path.
              </p>
            </div>
          </div>
          <div className={styles.actions}>
            <Button onClick={() => void handleBootstrap()} disabled={bootstrapMutation.isPending}>
              {bootstrapMutation.isPending ? "Bootstrapping Claude asset..." : "Bootstrap Claude Code asset"}
            </Button>
            <Notice>
              This keeps the existing Claude Code bootstrap route, but lands the governed result back on the current
              Agents surface.
            </Notice>
          </div>
        </Panel>
      ) : null}

      {agents.length
        ? groups.map((group) => (
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
                  onValidate={(currentAgent) => void handleValidation(currentAgent)}
                  isPublishing={publishMutation.isPending}
                  isUnpublishing={unpublishMutation.isPending}
                  isValidating={validationMutation.isPending}
                />
              ))}
            </div>
          ) : (
            <Notice>No agents in this section.</Notice>
          )}
        </Panel>
          ))
        : null}
    </section>
  );
}
