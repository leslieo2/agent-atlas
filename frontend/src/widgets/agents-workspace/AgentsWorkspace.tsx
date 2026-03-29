"use client";

import { ArrowUpRight } from "lucide-react";
import { useMemo, useState } from "react";
import {
  useDiscoveredAgentsQuery,
  usePublishAgentMutation,
  useUnpublishAgentMutation
} from "@/src/entities/agent/query";
import type { DiscoveredAgentRecord, RuntimeArtifactRecord } from "@/src/entities/agent/model";
import { Field } from "@/src/shared/ui/Field";
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

function runtimeArtifactStatus(agent: DiscoveredAgentRecord) {
  if (!agent.runtimeArtifact?.buildStatus) {
    return agent.publishState === "published" ? "legacy" : "not built";
  }
  return agent.runtimeArtifact.buildStatus;
}

function runtimeArtifactTone(runtimeArtifact?: RuntimeArtifactRecord | null) {
  if (!runtimeArtifact?.buildStatus) {
    return "warn" as const;
  }
  return runtimeArtifact.buildStatus === "ready" ? ("success" as const) : ("warn" as const);
}

function runtimeArtifactSummary(runtimeArtifact?: RuntimeArtifactRecord | null) {
  if (!runtimeArtifact) {
    return "legacy";
  }
  if (runtimeArtifact.imageRef) {
    return runtimeArtifact.imageRef;
  }
  if (runtimeArtifact.artifactRef) {
    return runtimeArtifact.artifactRef;
  }
  return "pending";
}

function shortSourceFingerprint(runtimeArtifact?: RuntimeArtifactRecord | null) {
  const fingerprint = runtimeArtifact?.sourceFingerprint;
  if (!fingerprint) {
    return "legacy";
  }
  return fingerprint.slice(0, 12);
}

function validationIssuesLabel(agent: DiscoveredAgentRecord) {
  if (agent.framework === "openai-agents-sdk") {
    return "OpenAI Agents SDK validation issues";
  }
  if (agent.framework === "langchain") {
    return "LangChain validation issues";
  }
  return "Unsupported framework issues";
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
          <StatusPill tone={runtimeArtifactTone(agent.runtimeArtifact)}>{`Build ${runtimeArtifactStatus(agent)}`}</StatusPill>
        </div>
      </div>

      {hasDraftChanges ? (
        <p className={styles.driftNotice}>Publish the current repository draft to refresh the runnable snapshot.</p>
      ) : null}

      <div className={styles.meta}>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Agent ID</span>
          <span className={`${styles.metaValue} mono`}>{agent.agentId}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Framework</span>
          <span className={styles.metaValue}>{agent.framework}</span>
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
          <span className={styles.metaLabel}>Artifact</span>
          <span className={`${styles.metaValue} mono`}>{runtimeArtifactSummary(agent.runtimeArtifact)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Source fingerprint</span>
          <span className={`${styles.metaValue} mono`}>{shortSourceFingerprint(agent.runtimeArtifact)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Last validated</span>
          <span className={styles.metaValue}>{new Date(agent.lastValidatedAt).toLocaleString("en")}</span>
        </div>
      </div>

      {!isValid ? (
        <div>
          <p className="page-eyebrow">{validationIssuesLabel(agent)}</p>
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
        {isPublished && isValid ? (
          <Button href={`/evals?agent=${encodeURIComponent(agent.agentId)}`} variant="secondary">
            Run eval <ArrowUpRight size={14} />
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
  const [frameworkFilter, setFrameworkFilter] = useState("all");
  const agents = useMemo(() => discoveredAgentsQuery.data ?? [], [discoveredAgentsQuery.data]);
  const frameworkOptions = useMemo(
    () => ["all", ...Array.from(new Set(agents.map((agent) => agent.framework))).sort()],
    [agents]
  );
  const filteredAgents = useMemo(
    () => (frameworkFilter === "all" ? agents : agents.filter((agent) => agent.framework === frameworkFilter)),
    [agents, frameworkFilter]
  );

  const groups = useMemo<AgentGroup[]>(
    () => [
      {
        title: "Ready",
        description: "Valid published agents ready to generate RL evaluation data.",
        items: filteredAgents.filter((agent) => getAgentReadiness(agent) === "ready")
      },
      {
        title: "Published with draft changes",
        description: "Current repository code differs from the published snapshot.",
        items: filteredAgents.filter((agent) => getAgentReadiness(agent) === "published_with_drift")
      },
      {
        title: "Draft",
        description: "Valid repository plugins that are not yet published for eval orchestration.",
        items: filteredAgents.filter((agent) => getAgentReadiness(agent) === "draft")
      },
      {
        title: "Invalid",
        description: "Discovered plugins that currently fail framework-specific contract validation.",
        items: filteredAgents.filter((agent) => getAgentReadiness(agent) === "invalid")
      }
    ],
    [filteredAgents]
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
            Discover repository-local plugins, publish framework-aware runnable snapshots, and keep invalid agents out
            of the RL data pipeline.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Visible <strong>{filteredAgents.length}</strong>
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
              {groups[0].items.length} ready / {groups[1].items.length} drifted / {groups[2].items.length} staged
            </span>
            <p className="page-info-detail">
              Re-publish drifted agents to refresh the snapshot that feeds future eval jobs and exports.
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

      <Panel tone="plain">
        <div className={styles.filterRow}>
          <Field label="Framework" htmlFor="agents-framework-filter">
            <select
              id="agents-framework-filter"
              value={frameworkFilter}
              onChange={(event) => setFrameworkFilter(event.target.value)}
            >
              {frameworkOptions.map((framework) => (
                <option key={framework} value={framework}>
                  {framework}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </Panel>

      {errorMessage ? <Notice>{errorMessage}</Notice> : null}
      {discoveredAgentsQuery.isLoading ? <Notice>Loading discovered agents...</Notice> : null}

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
