"use client";

import { ArrowUpRight } from "lucide-react";
import { getAgentValidationLifecycle } from "@/src/entities/agent/lifecycle";
import type { AgentRecord } from "@/src/entities/agent/model";
import { Button } from "@/src/shared/ui/Button";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import { StatusPill } from "@/src/shared/ui/StatusPill";
import type { AgentGroup } from "./model";
import {
  defaultRuntimeSummary,
  executionReferenceSummary,
  fallbackValidationTimestamp,
  formatValidationTimestamp,
  getAgentReadiness,
  nextStepLabel,
  readinessLabel,
  shortSourceFingerprint,
  validationEvidenceLabel,
  validationRunTone,
  validationSummaryStatus,
  validationTone
} from "./model";

function AgentCard({
  agent,
  onValidate,
  isValidating,
  styles
}: {
  agent: AgentRecord;
  onValidate: (agent: AgentRecord) => void;
  isValidating: boolean;
  styles: Record<string, string>;
}) {
  const validationLifecycle = getAgentValidationLifecycle(agent);
  const readiness = getAgentReadiness(agent);
  const isRunnableSnapshot = validationLifecycle.isSuccessful;

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
          <StatusPill tone={readiness === "ready" ? "success" : "warn"}>{readinessLabel(readiness)}</StatusPill>
          <StatusPill tone={validationTone(agent)}>{validationLifecycle.status}</StatusPill>
        </div>
      </div>

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
          <span className={styles.metaValue}>{new Date(fallbackValidationTimestamp(agent)).toLocaleString("en")}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Agent ID</span>
          <span className={`${styles.metaValue} mono`}>{agent.agentId}</span>
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
          <span className={styles.metaLabel}>Cataloged at</span>
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
          <span className={styles.metaLabel}>Default model</span>
          <span className={styles.metaValue}>{agent.defaultModel || "-"}</span>
        </div>
      </div>

      <div className={styles.actions}>
        <Button variant="secondary" onClick={() => onValidate(agent)} disabled={isValidating || validationLifecycle.isActive}>
          Run validation
        </Button>
        {isRunnableSnapshot ? (
          <Button href={`/experiments?agent=${encodeURIComponent(agent.agentId)}`} variant="secondary">
            Create experiment <ArrowUpRight size={14} />
          </Button>
        ) : null}
      </div>
    </article>
  );
}

export function AgentCatalogSections({
  agents,
  groups,
  isLoading,
  onValidate,
  styles,
  validationPending
}: {
  agents: AgentRecord[];
  groups: AgentGroup[];
  isLoading: boolean;
  onValidate: (agent: AgentRecord) => void;
  styles: Record<string, string>;
  validationPending: boolean;
}) {
  if (isLoading) {
    return <Notice>Loading agents...</Notice>;
  }

  if (!agents.length) {
    return (
      <Panel tone="plain">
        <div className="surface-header">
          <div>
            <p className="surface-kicker">No agents yet</p>
            <h3 className="panel-title">No ready assets yet</h3>
            <p className="muted-note">
              Use the governed entry panel above to import the first asset, run validation, and move ready assets
              into the catalog below.
            </p>
          </div>
        </div>
        <div className="page-stack">
          <Notice>Import starts the catalog entry here, and validation determines when an asset is ready to use.</Notice>
          <Notice>The catalog below only shows current governed assets after intake and validation.</Notice>
        </div>
      </Panel>
    );
  }

  return (
    <>
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
                  onValidate={onValidate}
                  isValidating={validationPending}
                  styles={styles}
                />
              ))}
            </div>
          ) : (
            <Notice>No agents in this section.</Notice>
          )}
        </Panel>
      ))}
    </>
  );
}
