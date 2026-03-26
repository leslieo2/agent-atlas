"use client";

import { ArrowUpRight } from "lucide-react";
import { useMemo } from "react";
import {
  useDiscoveredAgentsQuery,
  usePublishAgentMutation,
  useUnpublishAgentMutation
} from "@/src/entities/agent/query";
import type { DiscoveredAgentRecord } from "@/src/entities/agent/model";
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

function validationTone(agent: DiscoveredAgentRecord) {
  return agent.validationStatus === "valid" ? "success" : "error";
}

function publishTone(agent: DiscoveredAgentRecord) {
  return agent.publishState === "published" ? "success" : "warn";
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
          <StatusPill tone={publishTone(agent)}>{agent.publishState}</StatusPill>
          <StatusPill tone={validationTone(agent)}>{agent.validationStatus}</StatusPill>
        </div>
      </div>

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
      </div>

      {!isValid ? (
        <div>
          <p className="page-eyebrow">Validation issues</p>
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
        {isPublished ? (
          <Button variant="secondary" onClick={() => onUnpublish(agent.agentId)} disabled={isUnpublishing}>
            Unpublish
          </Button>
        ) : null}
        {isPublished && isValid ? (
          <Button href={`/playground?agent=${encodeURIComponent(agent.agentId)}`} variant="ghost">
            Open in Playground <ArrowUpRight size={14} />
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
  const agents = useMemo(() => discoveredAgentsQuery.data ?? [], [discoveredAgentsQuery.data]);

  const groups = useMemo<AgentGroup[]>(
    () => [
      {
        title: "Published",
        description: "Runnable agents exposed to Playground and run creation.",
        items: agents.filter((agent) => agent.publishState === "published" && agent.validationStatus === "valid")
      },
      {
        title: "Draft",
        description: "Valid repository plugins that are not yet exposed.",
        items: agents.filter((agent) => agent.publishState === "draft" && agent.validationStatus === "valid")
      },
      {
        title: "Invalid",
        description: "Discovered plugins that currently fail the OpenAI Agents SDK contract.",
        items: agents.filter((agent) => agent.validationStatus === "invalid")
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
            Discover repository-local plugins, publish runnable snapshots, and keep invalid agents out of Playground.
          </p>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Published" value={groups[0].items.length} />
        <MetricCard label="Draft" value={groups[1].items.length} />
        <MetricCard label="Invalid" value={groups[2].items.length} />
        <MetricCard label="Discovered" value={agents.length} />
      </div>

      {errorMessage ? <Notice>{errorMessage}</Notice> : null}
      {discoveredAgentsQuery.isLoading ? <Notice>Loading discovered agents...</Notice> : null}

      {groups.map((group) => (
        <Panel key={group.title} tone={group.title === "Published" ? "strong" : "default"} className={styles.group}>
          <div className="surface-header">
            <div>
              <p className="surface-kicker">{group.title}</p>
              <h3 className="panel-title">{group.description}</h3>
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
